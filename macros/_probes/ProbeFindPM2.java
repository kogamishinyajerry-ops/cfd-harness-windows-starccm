// ProbeFindPM2 - exhaustive search for ProbeManager class
import star.common.*;
import java.lang.reflect.*;

public class ProbeFindPM2 extends StarMacro {
    public void execute() {
        Simulation sim = getActiveSimulation();
        sim.println("=== ProbeFindPM2 START ===");
        String[] cand = {
            "star.common.ProbeManager",
            "star.probe.ProbeManager",
            "star.probes.ProbeManager",
            "star.common.probe.ProbeManager",
            "star.common.probes.ProbeManager",
            "star.common.ProbeData",
            "star.probe.PointProbe",
            "star.common.PointProbe",
            "star.probes.PointProbe",
            "star.common.probe.PointProbe",
        };
        for (String cn : cand) {
            try { Class c = Class.forName(cn); sim.println("OK: " + cn + " -> " + c.getName()); }
            catch (Throwable t) { sim.println("FAIL: " + cn); }
        }
        // also try: methods on Simulation named "getProbeManager"
        sim.println("--- sim.getProbeManager() and related ---");
        for (String mName : new String[]{"getProbeManager", "getProbes", "getPointProbes", "getProbesManager"}) {
            try {
                Method m = Simulation.class.getMethod(mName);
                Object o = m.invoke(sim);
                sim.println("  sim." + mName + "() -> " + (o == null ? "null" : o.getClass().getName()));
            } catch (Throwable t) {
                sim.println("  sim." + mName + " FAIL: " + t.getClass().getSimpleName() + ": " + t.getMessage());
            }
        }
        // also: methods on Region
        try {
            Region r = sim.get(RegionManager.class).getRegions().iterator().next();
            sim.println("Region class: " + r.getClass().getName());
            for (String mName : new String[]{"getProbeManager", "getProbes", "getPointProbes"}) {
                try {
                    Method m = r.getClass().getMethod(mName);
                    Object o = m.invoke(r);
                    sim.println("  reg." + mName + "() -> " + (o == null ? "null" : o.getClass().getName()));
                } catch (Throwable t) {
                    sim.println("  reg." + mName + " FAIL: " + t.getClass().getSimpleName());
                }
            }
        } catch (Throwable t) {
            sim.println("reg setup FAIL: " + t);
        }
        // Also: get the field function manager and dump its method list (looking for getFieldValue or similar)
        sim.println("--- ffm methods ---");
        try {
            FieldFunctionManager ffm = sim.getFieldFunctionManager();
            int count = 0;
            for (Method m : ffm.getClass().getMethods()) {
                String n = m.getName();
                if (n.startsWith("get") || n.startsWith("create") || n.startsWith("new")) {
                    sim.println("  " + n + "(" + m.getParameterCount() + " args) -> " + m.getReturnType().getSimpleName());
                    count++;
                }
            }
            sim.println("  total: " + count + " methods");
        } catch (Throwable t) {
            sim.println("ffm FAIL: " + t);
        }
        sim.println("=== ProbeFindPM2 END ===");
    }
}
