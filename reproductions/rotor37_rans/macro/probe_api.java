import star.common.*;
import star.base.neo.*;
import java.lang.reflect.*;
import java.util.*;

/** API probe for STAR-CCM+ 2402 R8: resolve turbo class/method signatures cheaply
 *  (no meshing/solving). All output prefixed PROBE> for easy extraction. */
public class probe_api extends StarMacro {
    Simulation sim;

    public void execute() {
        try {
            sim = getActiveSimulation();
            p("SIM active=" + (sim != null));

            dumpMethods("SIM", sim, new String[]{"Interface", "Frame", "Motion", "Reference", "Coordinate"});

            Object rm = tryCall(sim, "getReportManager");
            dumpMethods("ReportManager", rm, new String[]{"createReport", "create"});

            Object regm = tryCall(sim, "getRegionManager");
            dumpMethods("RegionManager", regm, new String[]{"create", "newRegions"});

            Object im = tryCall(sim, "getInterfaceManager");
            if (im != null) dumpMethods("InterfaceManager", im, new String[]{"create", "Periodic", "Interface"});

            // reference frame / motion managers (discover accessor on sim first)
            for (String acc : new String[]{"getReferenceFrameManager", "getMotionManager", "getCoordinateSystemManager"}) {
                Object mgr = tryCall(sim, acc);
                if (mgr != null) dumpMethods(acc, mgr, new String[]{"create", "Rotat", "Reference", "Motion"});
            }

            // empty region to introspect motion/reference-frame setters
            Object reg = tryCall(regm, "createEmptyRegion");
            if (reg != null) {
                dumpMethods("Region", reg, new String[]{"Reference", "Motion", "Rotat", "Frame", "getValues"});
            }

            p("---- CLASS RESOLUTION ----");
            String[] cands = {
                // coupled / density-based flow
                "star.coupledflow.CoupledFlowModel", "star.coupledflow.CoupledImplicitSolver",
                "star.coupledenergy.CoupledEnergyModel", "star.flow.CoupledFlowModel",
                // segregated (fallback)
                "star.segregatedflow.SegregatedFlowModel", "star.segregatedenergy.SegregatedFluidEnergyModel",
                // gas / eos
                "star.material.SingleComponentGasModel", "star.flow.IdealGasModel",
                "star.material.GasModel", "star.flow.ConstantDensityModel",
                // turbulence
                "star.turbulence.TurbulentModel", "star.turbulence.RansTurbulenceModel",
                "star.kwturb.KOmegaTurbulence", "star.kwturb.SstKwTurbModel", "star.kwturb.KwAllYplusWallTreatment",
                // space/time
                "star.common.ThreeDimensionalModel", "star.common.SteadyModel", "star.flow.SteadyModel",
                // boundaries
                "star.flow.StagnationBoundary", "star.common.StagnationBoundary",
                "star.flow.PressureBoundary", "star.common.PressureBoundary",
                "star.flow.MassFlowBoundary",
                // boundary profiles
                "star.flow.TotalPressureProfile", "star.common.TotalPressureProfile",
                "star.flow.TotalTemperatureProfile", "star.common.TotalTemperatureProfile",
                "star.common.StaticPressureProfile", "star.flow.StaticPressureProfile",
                // reports
                "star.base.report.MassFlowAverageReport", "star.flow.MassFlowReport",
                "star.base.report.MassFlowReport", "star.base.report.SurfaceAverageReport",
                "star.base.report.AreaAverageReport",
                // interfaces / periodic
                "star.common.PeriodicInterface", "star.meshing.PeriodicInterface",
                // reference frames / motion
                "star.common.RotatingReferenceFrame", "star.motion.RotatingReferenceFrame",
                "star.common.RotatingMotion", "star.motion.RotatingMotion",
                // meshing operations
                "star.meshing.MeshOperationManager", "star.dualmesher.DualAutoMesher",
                "star.trimmer.TrimmerAutoMesher", "star.prismmesher.PrismAutoMesher",
                "star.resurfacer.ResurfacerAutoMesher", "star.meshing.AutoMeshOperation",
            };
            for (String c : cands) testClass(c);

            p("---- BUILD CONTINUUM (coupled, ideal gas, SST) ----");
            buildContinuum();

            p("PROBE_DONE");
        } catch (Throwable t) {
            p("FATAL " + t);
            t.printStackTrace();
        }
    }

    void buildContinuum() {
        try {
            ContinuumManager cm = sim.get(ContinuumManager.class);
            PhysicsContinuum cont = cm.createContinuum(PhysicsContinuum.class);
            String[] order = {
                "star.common.ThreeDimensionalModel",
                "star.common.SteadyModel",
                "star.material.SingleComponentGasModel",
                "star.coupledflow.CoupledFlowModel",
                "star.flow.IdealGasModel",
                "star.coupledenergy.CoupledEnergyModel",
                "star.turbulence.TurbulentModel",
                "star.turbulence.RansTurbulenceModel",
                "star.kwturb.KOmegaTurbulence",
                "star.kwturb.SstKwTurbModel",
                "star.kwturb.KwAllYplusWallTreatment",
            };
            for (String fqn : order) {
                try {
                    Class<?> cl = Class.forName(fqn);
                    cont.enable(cl);
                    p("  ENABLED " + fqn);
                } catch (Throwable t) {
                    p("  enable FAIL " + fqn + " :: " + t.getClass().getSimpleName() + " " + t.getMessage());
                }
            }
        } catch (Throwable t) {
            p("buildContinuum FATAL " + t);
        }
    }

    // ---------- helpers ----------
    void p(String s) { System.out.println("PROBE> " + s); }

    Object tryCall(Object o, String m) {
        if (o == null) return null;
        try { return o.getClass().getMethod(m).invoke(o); }
        catch (Throwable t) { p("call " + m + " FAIL " + t.getClass().getSimpleName()); return null; }
    }

    void dumpMethods(String label, Object o, String[] keys) {
        if (o == null) { p(label + " = null"); return; }
        p("== " + label + " (" + o.getClass().getName() + ") methods matching " + Arrays.toString(keys));
        TreeSet<String> out = new TreeSet<>();
        for (Method m : o.getClass().getMethods()) {
            String name = m.getName();
            for (String k : keys) {
                if (name.toLowerCase().contains(k.toLowerCase())) {
                    StringBuilder sb = new StringBuilder(name).append("(");
                    Class<?>[] ps = m.getParameterTypes();
                    for (int i = 0; i < ps.length; i++) { if (i > 0) sb.append(","); sb.append(ps[i].getSimpleName()); }
                    sb.append(")->").append(m.getReturnType().getSimpleName());
                    out.add(sb.toString());
                    break;
                }
            }
        }
        for (String s : out) p("   " + s);
    }

    void testClass(String fqn) {
        try {
            Class<?> c = Class.forName(fqn);
            p("  OK   " + fqn);
        } catch (Throwable t) {
            p("  --   " + fqn);
        }
    }

    public static void main(String[] args) { new probe_api().execute(); }
}
