// Probe11.java — DEC-005 attempt 3/3
// Two candidate leads from Probe10:
//   (A) sim.getMeshManager().getCellInfo(Region, Vector) -> NeoProperty
//       (the canonical STAR-CCM+ API for cell data — may have a way
//       to get per-cell Ux values)
//   (B) sim.getRepresentationManager().getRegionRepresentations() -> Vector
//       (representations may have getInternalMesh + getCellCenters)
//
// Plus one more attempt: even if there's no getValue-at-point API,
// we can try a "MeshValue" or "SolutionValue" path on the Solution object.
// ProbeSol found Solution has no FieldValue* method, but we didn't
// walk superclasses of Solution. Try again here.
import star.common.*;
import star.base.neo.*;
import java.io.*;
import java.lang.reflect.*;
import java.util.*;

public class Probe11 extends StarMacro {
    public void execute() {
        Simulation sim = getActiveSimulation();
        sim.println("=== Probe11 START ===");
        PrintWriter pw = null;
        try {
            pw = new PrintWriter(new FileWriter(
                "D:\\CFD-harness-Windows-StarCCM\\probe11_cellinfo_diag.log"));
        } catch (Throwable t) { sim.println("can't open log: " + t); return; }
        try {
            RegionManager rm = sim.getRegionManager();
            Region reg = null;
            for (Object r : rm.getRegions()) { if (r instanceof Region) { reg = (Region) r; break; } }
            if (reg == null) { pw.println("no region"); pw.close(); return; }
            FieldFunctionManager ffm = sim.getFieldFunctionManager();
            FieldFunction velFF = ffm.getFunction("Velocity");
            FieldFunction uxFF = velFF.getComponentFunction(0);

            // (A) getCellInfo
            pw.println("=== (A) getCellInfo(Region, Vector) ===");
            try {
                MeshManager mm = sim.getMeshManager();
                Vector inVec = new Vector();
                // Probe: pass the region object, get NeoProperty
                Object np = mm.getClass().getMethod("getCellInfo", Region.class, Vector.class)
                    .invoke(mm, reg, inVec);
                pw.println("getCellInfo returned: " + (np == null ? "null" : np.getClass().getName()));
                if (np != null) {
                    // dump NeoProperty methods
                    for (Method m : np.getClass().getMethods()) {
                        String n = m.getName();
                        if (n.startsWith("get") || n.contains("Cell") || n.contains("Value") || n.contains("alue")) {
                            StringBuilder sb = new StringBuilder("  ");
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
            } catch (Throwable t) { pw.println("getCellInfo err: " + t); }

            // (B) RegionRepresentations
            pw.println("=== (B) RegionRepresentations ===");
            try {
                Object repMgr = sim.getClass().getMethod("getRepresentationManager").invoke(sim);
                Object reps = repMgr.getClass().getMethod("getRegionRepresentations").invoke(repMgr);
                pw.println("reps: " + (reps == null ? "null" : reps.getClass().getName()));
                if (reps instanceof Vector) {
                    pw.println("count: " + ((Vector<?>) reps).size());
                    for (Object r : (Vector<?>) reps) {
                        pw.println("rep: " + r.getClass().getName());
                        // dump methods
                        for (Method m : r.getClass().getMethods()) {
                            String n = m.getName();
                            if (n.contains("Mesh") || n.contains("Cell") || n.contains("Value") || n.contains("Sample") || n.contains("Internal")) {
                                StringBuilder sb = new StringBuilder("  ");
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
                        // Try getInternalMesh on the rep
                        try {
                            Object im = r.getClass().getMethod("getInternalMesh").invoke(r);
                            if (im != null) {
                                pw.println("rep.getInternalMesh -> " + im.getClass().getName());
                                for (Method m : im.getClass().getMethods()) {
                                    if (m.getName().contains("Cell") || m.getName().contains("Sample") || m.getName().contains("Value") || m.getName().contains("Point") || m.getName().contains("Coord")) {
                                        StringBuilder sb = new StringBuilder("    ");
                                        sb.append(m.getName()).append("(");
                                        Class<?>[] pts = m.getParameterTypes();
                                        for (int i = 0; i < pts.length; i++) {
                                            if (i > 0) sb.append(", ");
                                            sb.append(pts[i].getSimpleName());
                                        }
                                        sb.append(") -> ").append(m.getReturnType().getSimpleName());
                                        if (sb.length() < 130) pw.println(sb.toString());
                                    }
                                }
                                // Try getCellCenters
                                for (String mn : new String[]{"getCellCenters", "getCellCentroids", "getCenters", "getNodeCoordinates", "getNodes", "getCoordinates"}) {
                                    try {
                                        Method m = im.getClass().getMethod(mn);
                                        Object o = m.invoke(im);
                                        if (o == null) { pw.println("    " + mn + " -> null"); continue; }
                                        if (o instanceof double[]) pw.println("    " + mn + " -> double[len=" + ((double[]) o).length + "]");
                                        else if (o instanceof float[]) pw.println("    " + mn + " -> float[len=" + ((float[]) o).length + "]");
                                        else if (o instanceof int[]) pw.println("    " + mn + " -> int[len=" + ((int[]) o).length + "]");
                                        else pw.println("    " + mn + " -> " + o.getClass().getName());
                                    } catch (NoSuchMethodException nsme) { /* skip */ }
                                    catch (Throwable t) { pw.println("    " + mn + " err: " + t.getMessage()); }
                                }
                                // Try getInternalValue(FF) or similar
                                for (String mn : new String[]{"getInternalValue", "getValues", "getValues0", "getValue", "getXValues", "getYValues", "getZValues", "getArrays", "getFieldValues", "extractValues"}) {
                                    try {
                                        Method m = im.getClass().getMethod(mn, FieldFunction.class);
                                        Object o = m.invoke(im, uxFF);
                                        if (o == null) { pw.println("    " + mn + "(FF) -> null"); continue; }
                                        if (o instanceof double[]) pw.println("    " + mn + "(FF) -> double[len=" + ((double[]) o).length + "] first=" + ((double[]) o)[0]);
                                        else if (o instanceof float[]) pw.println("    " + mn + "(FF) -> float[len=" + ((float[]) o).length + "]");
                                        else pw.println("    " + mn + "(FF) -> " + o.getClass().getName());
                                    } catch (NoSuchMethodException nsme) { /* skip */ }
                                    catch (Throwable t) { pw.println("    " + mn + "(FF) err: " + t.getMessage()); }
                                }
                            }
                        } catch (Throwable t) { pw.println("rep.getInternalMesh err: " + t); }
                    }
                }
            } catch (Throwable t) { pw.println("(B) err: " + t); }

            // (C) Try Solution object deeper walk
            pw.println("=== (C) Solution superclass walk ===");
            try {
                Solution sol = sim.getSolution();
                for (Class<?> c = sol.getClass().getSuperclass(); c != null && c != Object.class; c = c.getSuperclass()) {
                    pw.println("Solution super: " + c.getName());
                    for (Method m : c.getDeclaredMethods()) {
                        String n = m.getName();
                        if (n.contains("alue") || n.contains("oord") || n.contains("ample") || n.contains("valuate") || n.contains("og") || n.contains("oint")) {
                            StringBuilder sb = new StringBuilder("  ");
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
            } catch (Throwable t) { pw.println("(C) err: " + t); }

        } catch (Throwable t) {
            pw.println("FATAL: " + t);
        }
        pw.close();
        sim.println("=== Probe11 END ===");
    }
}
