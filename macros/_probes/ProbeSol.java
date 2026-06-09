// ProbeSol - dump Solution methods + try direct field value eval at point
import star.common.*;
import java.lang.reflect.*;

public class ProbeSol extends StarMacro {
    public void execute() {
        Simulation sim = getActiveSimulation();
        sim.println("=== ProbeSol START ===");
        try {
            Solution sol = sim.getSolution();
            sim.println("Solution class: " + sol.getClass().getName());
            for (Method m : sol.getClass().getMethods()) {
                String n = m.getName();
                if (n.contains("Field") || n.contains("Value") || n.contains("Point") || n.contains("Evaluate") || n.contains("Sample") || n.contains("Probe")) {
                    StringBuilder sb = new StringBuilder("  " + n + "(");
                    Class<?>[] pts = m.getParameterTypes();
                    for (int i = 0; i < pts.length; i++) {
                        if (i > 0) sb.append(", ");
                        sb.append(pts[i].getSimpleName());
                    }
                    sb.append(") -> ").append(m.getReturnType().getSimpleName());
                    if (sb.length() < 130) sim.println(sb.toString());
                }
            }
            // Try the report path: create SumReport bound to Ux component on cavity region
            sim.println("--- try report path ---");
            FieldFunctionManager ffm = sim.getFieldFunctionManager();
            FieldFunction velFF = ffm.getFunction("Velocity");
            sim.println("velFF: " + velFF.getClass().getName());
            FieldFunction uxFF = velFF.getComponentFunction(0);
            sim.println("uxFF: " + (uxFF == null ? "null" : uxFF.getClass().getName()));
            FieldFunction magFF = velFF.getMagnitudeFunction();
            sim.println("magFF: " + (magFF == null ? "null" : magFF.getClass().getName()));

            // Create SumReport on cavity region
            RegionManager rm = sim.getRegionManager();
            sim.println("rm class: " + rm.getClass().getName());
            // region
            Region reg = rm.getRegions().iterator().next();
            sim.println("region: " + reg.getPresentationName());

            // Get report manager
            Object repMgr = sim.getClass().getMethod("getReportManager").invoke(sim);
            sim.println("repMgr class: " + repMgr.getClass().getName());
            for (Method m : repMgr.getClass().getMethods()) {
                if (m.getName().contains("create") || m.getName().contains("Report")) {
                    sim.println("    " + m.getName() + "(" + m.getParameterCount() + ") -> " + m.getReturnType().getSimpleName());
                }
            }
            // Create SumReport (try several packages)
            Class<?> sumCls = null;
            for (String cn : new String[]{"star.common.SumReport", "star.base.report.SumReport"}) {
                try { sumCls = Class.forName(cn); break; } catch (Throwable t) {}
            }
            if (sumCls == null) { sim.println("no SumReport class"); return; }
            sim.println("SumReport class: " + sumCls.getName());
            Object rep = repMgr.getClass().getMethod("createReport", Class.class).invoke(repMgr, sumCls);
            sim.println("SumReport created: " + rep.getClass().getName());
            // bind FF
            try {
                rep.getClass().getMethod("setFieldFunction", FieldFunction.class).invoke(rep, uxFF);
                sim.println("setFieldFunction OK");
            } catch (Throwable t) {
                sim.println("setFieldFunction FAIL: " + t);
            }
            // bind parts to region
            try {
                Object parts = rep.getClass().getMethod("getParts").invoke(rep);
                java.util.List<Region> regs = new java.util.ArrayList<>();
                regs.add(reg);
                parts.getClass().getMethod("setObjects", java.util.Collection.class).invoke(parts, regs);
                sim.println("setParts OK");
            } catch (Throwable t) {
                sim.println("setParts FAIL: " + t);
            }
            // Get value via various getters
            for (String gName : new String[]{"getReportMonitorValue", "getMonitorValue", "getValue", "getSum", "getAverage"}) {
                try {
                    Method g = rep.getClass().getMethod(gName);
                    Object v = g.invoke(rep);
                    sim.println("  " + gName + "() -> " + (v == null ? "null" : v.toString()));
                } catch (Throwable t) {
                    sim.println("  " + gName + " FAIL: " + t.getClass().getSimpleName());
                }
            }
            // Cleanup
            try { repMgr.getClass().getMethod("removeReport", rep.getClass()).invoke(repMgr, rep); } catch (Throwable t) {}

        } catch (Throwable t) {
            sim.println("FATAL: " + t);
            t.printStackTrace();
        }
        sim.println("=== ProbeSol END ===");
    }
}