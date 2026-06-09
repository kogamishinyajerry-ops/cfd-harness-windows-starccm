// ProbeBlockPart - find the right way to create a SimpleBlockPart
import star.common.*;
import java.lang.reflect.*;

public class ProbeBlockPart extends StarMacro {
    public void execute() {
        Simulation sim = getActiveSimulation();
        sim.println("=== ProbeBlockPart START ===");
        try {
            RegionManager rm = sim.getRegionManager();
            sim.println("rm class: " + rm.getClass().getName());
            // enumerate methods with "create" or "Part" or "Block"
            for (Method m : rm.getClass().getMethods()) {
                String n = m.getName();
                if (n.contains("create") || n.contains("Part") || n.contains("Block") || n.contains("New")) {
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
            // also: probe GeometryPartManager
            sim.println("--- GeometryPartManager methods ---");
            GeometryPartManager gpm = sim.get(GeometryPartManager.class);
            for (Method m : gpm.getClass().getMethods()) {
                String n = m.getName();
                if (n.contains("create") || n.contains("Block") || n.contains("New")) {
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
        } catch (Throwable t) {
            sim.println("FATAL: " + t);
        }
        sim.println("=== ProbeBlockPart END ===");
    }
}