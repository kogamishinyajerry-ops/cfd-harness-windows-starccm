// ProbeFFM - enumerate all FFM methods, find the right way to sample a FF
import star.common.*;
import java.lang.reflect.*;

public class ProbeFFM extends StarMacro {
    public void execute() {
        Simulation sim = getActiveSimulation();
        sim.println("=== ProbeFFM START ===");
        try {
            FieldFunctionManager ffm = sim.getFieldFunctionManager();
            sim.println("FFM class: " + ffm.getClass().getName());
            // All public methods
            for (Method m : ffm.getClass().getMethods()) {
                String n = m.getName();
                Class<?>[] pts = m.getParameterTypes();
                StringBuilder sb = new StringBuilder("  " + n + "(");
                for (int i = 0; i < pts.length; i++) {
                    if (i > 0) sb.append(", ");
                    sb.append(pts[i].getSimpleName());
                }
                sb.append(") -> ").append(m.getReturnType().getSimpleName());
                if (sb.length() < 130) sim.println(sb.toString());
            }
            // Also try: get Velocity FF and dump its methods
            sim.println("--- velocity FF methods ---");
            for (String fn : new String[]{"Velocity", "Velocity: Magnitude"}) {
                FieldFunction ff = null;
                try { ff = ffm.getFunction(fn); } catch (Throwable t) {}
                if (ff == null) {
                    // try reflective getFieldFunction
                    try {
                        Method m = ffm.getClass().getMethod("getFieldFunction", String.class);
                        Object o = m.invoke(ffm, fn);
                        if (o != null) ff = (FieldFunction) o;
                    } catch (Throwable t) {}
                }
                if (ff == null) { sim.println("no " + fn); continue; }
                sim.println("FF " + fn + ": " + ff.getClass().getName());
                for (Method m : ff.getClass().getMethods()) {
                    String n = m.getName();
                    if (n.startsWith("get") || n.startsWith("eval") || n.startsWith("sample") || n.startsWith("probe") || n.startsWith("extract")) {
                        StringBuilder sb = new StringBuilder("    " + n + "(");
                        Class<?>[] pts = m.getParameterTypes();
                        for (int i = 0; i < pts.length; i++) {
                            if (i > 0) sb.append(", ");
                            sb.append(pts[i].getSimpleName());
                        }
                        sb.append(") -> ").append(m.getReturnType().getSimpleName());
                        if (sb.length() < 130) sim.println(sb.toString());
                    }
                }
            }
            // Also: try to use ReportManager to create a PointReport
            sim.println("--- sim report methods ---");
            for (String mn : new String[]{"getReportManager", "getReportsManager", "getMonitorManager"}) {
                try {
                    Method m = Simulation.class.getMethod(mn);
                    Object o = m.invoke(sim);
                    sim.println("  sim." + mn + "() -> " + (o == null ? "null" : o.getClass().getName()));
                    if (o != null) {
                        for (Method m2 : o.getClass().getMethods()) {
                            String n2 = m2.getName();
                            if (n2.startsWith("create") || n2.startsWith("new") || n2.startsWith("getPoint") || n2.startsWith("getMax")) {
                                sim.println("    " + n2 + "(" + m2.getParameterCount() + ") -> " + m2.getReturnType().getSimpleName());
                            }
                        }
                    }
                } catch (Throwable t) {
                    sim.println("  sim." + mn + " FAIL: " + t.getClass().getSimpleName());
                }
            }
        } catch (Throwable t) {
            sim.println("FATAL: " + t);
        }
        sim.println("=== ProbeFFM END ===");
    }
}
