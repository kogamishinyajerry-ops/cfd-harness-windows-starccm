// ProbeVCF - methods on VectorComponentFieldFunction (the scalar Ux FF)
import star.common.*;
import java.lang.reflect.*;

public class ProbeVCF extends StarMacro {
    public void execute() {
        Simulation sim = getActiveSimulation();
        sim.println("=== ProbeVCF START ===");
        try {
            FieldFunctionManager ffm = sim.getFieldFunctionManager();
            FieldFunction velFF = ffm.getFunction("Velocity");
            FieldFunction uxFF = velFF.getComponentFunction(0);
            sim.println("uxFF class: " + uxFF.getClass().getName());
            // enumerate all methods
            int n = 0;
            for (Method m : uxFF.getClass().getMethods()) {
                String name = m.getName();
                if (name.contains("Value") || name.contains("Eval") || name.contains("Sample") || name.contains("Probe")) {
                    StringBuilder sb = new StringBuilder("  " + name + "(");
                    Class<?>[] pts = m.getParameterTypes();
                    for (int i = 0; i < pts.length; i++) {
                        if (i > 0) sb.append(", ");
                        sb.append(pts[i].getSimpleName());
                    }
                    sb.append(") -> ").append(m.getReturnType().getSimpleName());
                    if (sb.length() < 130) { sim.println(sb.toString()); n++; }
                }
            }
            sim.println("(" + n + " methods listed)");
            // Also: all getValue overloads
            sim.println("--- all getValue overloads ---");
            for (Method m : uxFF.getClass().getMethods()) {
                if (m.getName().equals("getValue")) {
                    StringBuilder sb = new StringBuilder("  getValue(");
                    Class<?>[] pts = m.getParameterTypes();
                    for (int i = 0; i < pts.length; i++) {
                        if (i > 0) sb.append(", ");
                        sb.append(pts[i].getName());
                    }
                    sb.append(") -> ").append(m.getReturnType().getName());
                    sim.println(sb.toString());
                }
            }
            // Solution class methods
            sim.println("--- Solution methods (getFieldValue etc) ---");
            Solution sol = sim.getSolution();
            for (Method m : sol.getClass().getMethods()) {
                String name = m.getName();
                if (name.contains("Field") || name.contains("Point")) {
                    StringBuilder sb = new StringBuilder("  " + name + "(");
                    Class<?>[] pts = m.getParameterTypes();
                    for (int i = 0; i < pts.length; i++) {
                        if (i > 0) sb.append(", ");
                        sb.append(pts[i].getSimpleName());
                    }
                    sb.append(") -> ").append(m.getReturnType().getSimpleName());
                    if (sb.length() < 130) sim.println(sb.toString());
                }
            }
        } catch (Throwable t) {
            sim.println("FATAL: " + t);
        }
        sim.println("=== ProbeVCF END ===");
    }
}