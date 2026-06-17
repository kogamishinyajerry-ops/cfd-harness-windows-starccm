import star.common.*;
import star.base.neo.*;
import star.meshing.*;
import java.lang.reflect.*;
import java.util.*;

/** Probe #2b (setup-only): import named STL, region, assign coupled/ideal-gas/SST
 *  continuum, THEN introspect stagnation/pressure boundary value classes, region
 *  reference-frame value, reference-frame manager, periodic interface. Output PROBE2>. */
public class probe_setup extends StarMacro {
    Simulation sim;
    String STL = "D:\\CFD-harness-Windows-StarCCM\\reproductions\\rotor37_rans\\geom\\fluid_passage_named.stl";

    public void execute() {
        sim = getActiveSimulation();
        p("start active=" + (sim != null));

        Object part = null;
        try {
            Object pim = simGet("star.meshing.PartImportManager");
            Units m = sim.getUnitsManager().getPreferredUnits(new Dimensions.Builder().length(1).build());
            pim.getClass().getMethod("importStlPart", String.class, String.class, Units.class,
                    boolean.class, double.class, boolean.class, boolean.class)
                .invoke(pim, STL, "OneSurfacePerPatch", m, true, 1.0E-5, false, false);
            Object gpm = simGet("star.common.GeometryPartManager");
            Collection<?> parts = (Collection<?>) gpm.getClass().getMethod("getObjects").invoke(gpm);
            part = parts.iterator().next();
            p("imported part=" + pres(part) + " surfaces=" + ((Collection<?>) part.getClass().getMethod("getPartSurfaces").invoke(part)).size());
        } catch (Throwable t) { p("IMPORT FAIL " + root(t)); return; }

        Region reg = null;
        try {
            Object regm = sim.getRegionManager();
            ArrayList<Object> plist = new ArrayList<>(); plist.add(part);
            regm.getClass().getMethod("newRegionsFromParts", Collection.class, String.class, String.class, String.class, boolean.class)
                .invoke(regm, plist, "OneRegion", "OneBoundaryPerPartSurface", "OneFeatureCurve", true);
            for (Region r : sim.getRegionManager().getRegions()) { reg = r; break; }
            p("region=" + pres(reg));
        } catch (Throwable t) { p("REGION FAIL " + root(t)); return; }

        // ---- continuum: coupled + ideal gas + SST, then assign to region ----
        Object cont = null;
        try {
            ContinuumManager cm = sim.get(ContinuumManager.class);
            cont = cm.createContinuum(PhysicsContinuum.class);
            for (String fqn : new String[]{
                    "star.common.SteadyModel", "star.material.SingleComponentGasModel",
                    "star.coupledflow.CoupledFlowModel", "star.flow.IdealGasModel",
                    "star.turbulence.TurbulentModel", "star.turbulence.RansTurbulenceModel",
                    "star.kwturb.KOmegaTurbulence", "star.kwturb.SstKwTurbModel", "star.kwturb.KwAllYplusWallTreatment"}) {
                try { ((PhysicsContinuum) cont).enable(Class.forName(fqn)); } catch (Throwable t) { p("enable FAIL " + fqn + " " + root(t)); }
            }
            // assign region to continuum
            boolean assigned = false;
            for (Class<?> pt : new Class<?>[]{simClass("star.common.Region"), Object.class}) {
                try { cont.getClass().getMethod("add", pt).invoke(cont, reg); assigned = true; p("continuum.add(region) OK via " + pt.getSimpleName()); break; }
                catch (Throwable t) {}
            }
            if (!assigned) p("continuum assign FAIL (will introspect region setters)");
            dumpMethods("PhysicsContinuum", cont, new String[]{"add", "Region"});
        } catch (Throwable t) { p("CONTINUUM FAIL " + root(t)); }

        // ---- region values (reference frame value) ----
        try {
            Object rv = reg.getClass().getMethod("getValues").invoke(reg);
            dumpObjects("Region.getValues", rv);
        } catch (Throwable t) { p("Region.getValues FAIL " + root(t)); }
        try { dumpMethods("Region", reg, new String[]{"Reference", "Motion", "Frame"}); } catch (Throwable t) {}

        // ---- boundaries + stagnation/pressure value classes ----
        Object per1 = null, per2 = null;
        try {
            Object bm = reg.getBoundaryManager();
            Collection<?> bnds = (Collection<?>) bm.getClass().getMethod("getBoundaries").invoke(bm);
            Object inlet = null, outlet = null;
            for (Object b : bnds) {
                String nm = pres(b).toLowerCase();
                if (nm.contains("inlet")) inlet = b; else if (nm.contains("outlet")) outlet = b;
                else if (nm.contains("per1")) per1 = b; else if (nm.contains("per2")) per2 = b;
            }
            setTypeAndDump(inlet, "star.common.StagnationBoundary", "INLET");
            setTypeAndDump(outlet, "star.common.PressureBoundary", "OUTLET");
        } catch (Throwable t) { p("BOUNDARY FAIL " + root(t)); }

        // ---- periodic interface ----
        try {
            if (per1 != null && per2 != null) {
                Object im = sim.getInterfaceManager();
                Object itf = im.getClass().getMethod("createDirectInterface",
                        simClass("star.common.Boundary"), simClass("star.common.Boundary")).invoke(im, per1, per2);
                p("interface class=" + itf.getClass().getName() + " name=" + pres(itf));
                dumpMethods("Interface", itf, new String[]{"Periodic", "Topology", "Transform", "Rotat", "Config", "getValues", "getConditions"});
                dumpObjects("Interface.getConditions", tryCall(itf, "getConditions"));
                dumpObjects("Interface.getValues", tryCall(itf, "getValues"));
            }
        } catch (Throwable t) { p("INTERFACE FAIL " + root(t)); }

        // ---- reference frame manager + rotating frame ----
        try {
            Object rfm = null;
            try { rfm = sim.getClass().getMethod("getReferenceFrameManager").invoke(sim); } catch (Throwable t) { p("getReferenceFrameManager FAIL " + root(t)); }
            if (rfm == null) rfm = simGet("star.common.AbstractReferenceFrameManager", "star.common.ReferenceFrameManager");
            if (rfm != null) {
                p("RFM=" + rfm.getClass().getName());
                dumpMethods("RFM", rfm, new String[]{"create", "Rotat", "Local"});
                for (String m : new String[]{"createLocalReferenceFrame"}) {
                    try {
                        Object rf = rfm.getClass().getMethod(m, Class.class).invoke(rfm, simClass("star.motion.RotatingReferenceFrame"));
                        p("created RotatingReferenceFrame=" + rf.getClass().getName());
                        dumpMethods("RotRF", rf, new String[]{"Rotat", "Axis", "Rate", "Origin", "Coordinate", "getValues", "getConditions"});
                        dumpObjects("RotRF.getValues", tryCall(rf, "getValues"));
                        break;
                    } catch (Throwable t) { p(m + " FAIL " + root(t)); }
                }
            } else p("RFM null");
        } catch (Throwable t) { p("RFM block FAIL " + root(t)); }

        // ---- report classes ----
        for (String fqn : new String[]{"star.flow.MassFlowAverageReport", "star.base.report.MassFlowAverageReport",
                "star.flow.MassFlowReport", "star.base.report.SurfaceAverageReport", "star.base.report.AreaAverageReport"}) {
            try { Class.forName(fqn); p("report OK " + fqn); } catch (Throwable t) { p("report --  " + fqn); }
        }

        p("PROBE2_DONE");
    }

    void setTypeAndDump(Object bnd, String typeFqn, String tag) {
        if (bnd == null) { p(tag + " null"); return; }
        try {
            Object ctm = simGet("star.common.ConditionTypeManager");
            Object bt = ctm.getClass().getMethod("get", Class.class).invoke(ctm, simClass(typeFqn));
            bnd.getClass().getMethod("setBoundaryType", simClass("star.common.BoundaryType")).invoke(bnd, bt);
            p(tag + " type=" + typeFqn + " OK");
            dumpObjects(tag + ".conditions", tryCall(bnd, "getConditions"));
            dumpObjects(tag + ".values", bnd.getClass().getMethod("getValues").invoke(bnd));
        } catch (Throwable t) { p(tag + " FAIL " + root(t)); }
    }

    void p(String s) { System.out.println("PROBE2> " + s); }
    String pres(Object o) { try { return (String) o.getClass().getMethod("getPresentationName").invoke(o); } catch (Throwable t) { return "?"; } }
    Class<?> simClass(String fqn) { try { return Class.forName(fqn); } catch (Throwable t) { return null; } }
    Object simGet(String... fqns) {
        for (String f : fqns) { try { return sim.getClass().getMethod("get", Class.class).invoke(sim, Class.forName(f)); } catch (Throwable t) {} }
        return null;
    }
    Object tryCall(Object o, String m) { if (o == null) return null; try { return o.getClass().getMethod(m).invoke(o); } catch (Throwable t) { return null; } }
    String root(Throwable t) { Throwable r = t; while (r.getCause() != null) r = r.getCause(); return r.getClass().getSimpleName() + ":" + r.getMessage(); }
    void dumpMethods(String label, Object o, String[] keys) {
        if (o == null) { p(label + " null"); return; }
        p("== " + label + " (" + o.getClass().getName() + ")");
        TreeSet<String> out = new TreeSet<>();
        for (Method mm : o.getClass().getMethods()) for (String k : keys) if (mm.getName().toLowerCase().contains(k.toLowerCase())) {
            StringBuilder sb = new StringBuilder(mm.getName()).append("(");
            Class<?>[] ps = mm.getParameterTypes();
            for (int i = 0; i < ps.length; i++) { if (i > 0) sb.append(","); sb.append(ps[i].getSimpleName()); }
            out.add(sb.append(")->").append(mm.getReturnType().getSimpleName()).toString()); break;
        }
        for (String s : out) p("   " + s);
    }
    void dumpObjects(String label, Object mgr) {
        if (mgr == null) { p(label + " null"); return; }
        try {
            Collection<?> objs = (Collection<?>) mgr.getClass().getMethod("getObjects").invoke(mgr);
            p("== " + label + " n=" + objs.size());
            for (Object o : objs) p("   " + o.getClass().getName() + " '" + pres(o) + "'");
        } catch (Throwable t) { p(label + " FAIL " + root(t)); }
    }
    public static void main(String[] a) { new probe_setup().execute(); }
}
