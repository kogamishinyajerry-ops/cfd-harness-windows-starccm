import star.common.*;
import star.base.neo.*;
import star.motion.*;
import java.lang.reflect.*;
import java.util.*;

/** Probe #6: reach SimulationTools -> reference-frame/motion managers, create a
 *  rotating reference frame + motion, and discover region assignment. Output PROBE6>. */
public class probe_tools extends StarMacro {
    Simulation sim;
    public void execute() {
        sim = getActiveSimulation();
        p("start");
        Object tools = null;
        try {
            for (Object o : (Collection<?>) sim.getClass().getMethod("getChildren").invoke(sim))
                if (o.getClass().getName().equals("star.common.SimulationTools")) { tools = o; break; }
            p("tools=" + (tools == null ? "null" : tools.getClass().getName()));
        } catch (Throwable t) { p("tools find FAIL " + root(t)); }
        if (tools == null) { p("PROBE6_DONE"); return; }

        dumpMethods("SimulationTools", tools, new String[]{"Reference", "Motion", "Frame", "get"});
        // enumerate tools children
        try {
            p("== tools children:");
            for (Object o : (Collection<?>) tools.getClass().getMethod("getChildren").invoke(tools)) {
                String cn = o.getClass().getName();
                if (cn.toLowerCase().contains("motion") || cn.toLowerCase().contains("frame") || cn.toLowerCase().contains("reference"))
                    p("   *" + cn + " '" + pres(o) + "'");
            }
        } catch (Throwable t) { p("tools children FAIL " + root(t)); }

        // reference frame manager
        Object rfm = tryCall(tools, "getReferenceFrameManager");
        if (rfm == null) rfm = toolsGet(tools, "star.common.AbstractReferenceFrameManager");
        p("rfm=" + (rfm == null ? "null" : rfm.getClass().getName()));
        Object rrf = null;
        if (rfm != null) {
            dumpMethods("RFM", rfm, new String[]{"create", "Rotat", "Local"});
            for (String mn : new String[]{"createLocalReferenceFrame"}) {
                try { rrf = rfm.getClass().getMethod(mn, Class.class).invoke(rfm, RotatingReferenceFrame.class);
                    p(mn + " OK -> " + rrf.getClass().getName()); break; }
                catch (Throwable t) { p(mn + " FAIL " + root(t)); }
            }
        }
        if (rrf != null) {
            dumpMethods("RotRF", rrf, new String[]{"set", "Rotat", "Axis", "Rate", "Origin", "Coordinate", "Values"});
            dumpObjects("RotRF.values", tryCall(rrf, "getValues"));
            dumpObjects("RotRF.conditions", tryCall(rrf, "getConditions"));
        }

        // motion manager
        Object mm = tryCall(tools, "getMotionManager");
        if (mm == null) mm = toolsGet(tools, "star.motion.MotionManager");
        p("mm=" + (mm == null ? "null" : mm.getClass().getName()));
        Object rot = null;
        if (mm != null) {
            dumpMethods("MotionManager", mm, new String[]{"create", "Motion"});
            try { rot = mm.getClass().getMethod("createMotion", Class.class).invoke(mm, RotatingMotion.class);
                p("createMotion OK -> " + rot.getClass().getName()); }
            catch (Throwable t) { p("createMotion FAIL " + root(t)); }
        }
        if (rot != null) dumpMethods("RotatingMotion", rot, new String[]{"Rotat", "Axis", "Rate", "Origin", "Coordinate", "Direction", "Values"});

        // region + continuum, then check region values for reference-frame/motion spec
        try {
            Region reg = sim.getRegionManager().createEmptyRegion();
            ContinuumManager cm = sim.get(ContinuumManager.class);
            PhysicsContinuum cont = cm.createContinuum(PhysicsContinuum.class);
            for (String f : new String[]{"star.common.SteadyModel","star.material.SingleComponentGasModel",
                    "star.coupledflow.CoupledFlowModel","star.flow.IdealGasModel"})
                try { cont.enable(Class.forName(f)); } catch (Throwable t) {}
            cont.getClass().getMethod("add", Class.forName("star.common.Region")).invoke(cont, reg);
            dumpObjects("Region.values(after frame+motion exist)", tryCall(reg, "getValues"));
            dumpMethods("Region", reg, new String[]{"Motion", "Reference", "Frame"});
        } catch (Throwable t) { p("region FAIL " + root(t)); }

        p("PROBE6_DONE");
    }
    Object toolsGet(Object tools, String fqn) {
        try { return tools.getClass().getMethod("get", Class.class).invoke(tools, Class.forName(fqn)); } catch (Throwable t) { return null; }
    }
    void p(String s) { System.out.println("PROBE6> " + s); }
    String pres(Object o) { try { return (String) o.getClass().getMethod("getPresentationName").invoke(o); } catch (Throwable t) { return "?"; } }
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
        try { Collection<?> objs = (Collection<?>) mgr.getClass().getMethod("getObjects").invoke(mgr);
            p("== " + label + " n=" + objs.size());
            for (Object o : objs) p("   " + o.getClass().getName() + " '" + pres(o) + "'");
        } catch (Throwable t) { p(label + " FAIL " + root(t)); }
    }
    public static void main(String[] a) { new probe_tools().execute(); }
}
