// Probe15.java — DEC-005 attempt 7/7
// Try to use STAR-CCM+ built-in {Position} field function directly
// (not via createFieldFunction + setDefinition), and see if
// splitRegionsByFunction works on it.
import star.common.*;
import star.base.neo.*;
import java.io.*;
import java.lang.reflect.*;
import java.util.*;

public class Probe15 extends StarMacro {
    public void execute() {
        Simulation sim = getActiveSimulation();
        sim.println("=== Probe15 START ===");
        PrintWriter pw = null;
        try {
            pw = new PrintWriter(new FileWriter(
                "D:\\CFD-harness-Windows-StarCCM\\probe15_position_ff.log"));
        } catch (Throwable t) { sim.println("can't open log: " + t); return; }
        try {
            FieldFunctionManager ffm = sim.getFieldFunctionManager();
            Object mm = sim.getMeshManager();
            RegionManager rm = sim.getRegionManager();
            Region reg = null;
            for (Object r : rm.getRegions()) { if (r instanceof Region) { reg = (Region) r; break; } }

            // 1) Try built-in Position FFs (different naming conventions)
            String[] names = {
                "Position", "Position: Magnitude", "Position[0]", "Position[1]", "Position[2]",
                "Coordinate", "Coordinate: Magnitude", "CoordinateX", "CoordinateY", "CoordinateZ",
                "PointCoordinate", "PointCoordinate: Magnitude",
                "PointCoordinate[0]", "PointCoordinate[1]", "PointCoordinate[2]",
                "CellPosition", "CellCoordinate", "NodePosition", "NodeCoordinate",
                "Centroid", "CellCentroid",
                "Y", "y", "X", "x", "Z", "z"
            };
            for (String n : names) {
                try {
                    FieldFunction f = ffm.getFunction(n);
                    if (f != null) {
                        // check if it's a real (non-sentinel) FF
                        String pn = f.getPresentationName();
                        if (pn != null && !pn.startsWith("<")) {
                            pw.println("FOUND: " + n + " -> " + f.getClass().getSimpleName() + " pres=" + pn);
                            // check if it can be previewSplit
                            try {
                                Object n_splits = mm.getClass().getMethod("previewSplitRegions", FieldFunction.class, Collection.class)
                                    .invoke(mm, f, java.util.Collections.singletonList(reg));
                                pw.println("  previewSplitRegions(" + n + ") -> " + n_splits);
                            } catch (Throwable t) { pw.println("  previewSplitRegions(" + n + ") FAIL: " + t.getMessage()); }
                        }
                    }
                } catch (Throwable t) { /* skip */ }
            }

            // 2) Try to compute a Ux-Y field by splitting with a different (active) field
            //    Force-evaluate a user FF by re-initializing the solution? No, that's too heavy.
            // 
            // Instead: try splitting with a VectorFieldFunction — see if sim.getSolution()
            // has a getFieldValue or evaluate method that we missed
            pw.println("=== Solution class method walk (deeper) ===");
            Solution sol = sim.getSolution();
            pw.println("Solution class: " + sol.getClass().getName());
            for (Class<?> c = sol.getClass(); c != null && c != Object.class; c = c.getSuperclass()) {
                pw.println("  super: " + c.getName());
                for (Method m : c.getDeclaredMethods()) {
                    String n = m.getName();
                    if (n.contains("alue") || n.contains("oord") || n.contains("ample") || n.contains("valuate") || n.contains("itialize") || n.contains("ield") || n.contains("ompute")) {
                        StringBuilder sb = new StringBuilder("    ");
                        sb.append(n).append("(");
                        Class<?>[] pts = m.getParameterTypes();
                        for (int i = 0; i < pts.length; i++) {
                            if (i > 0) sb.append(", ");
                            sb.append(pts[i].getSimpleName());
                        }
                        sb.append(") -> ").append(m.getReturnType().getSimpleName());
                        if (sb.length() < 130) pw.println(sb.toString());
                    }
                }
            }

        } catch (Throwable t) {
            pw.println("FATAL: " + t);
        }
        pw.close();
        sim.println("=== Probe15 END ===");
    }
}
