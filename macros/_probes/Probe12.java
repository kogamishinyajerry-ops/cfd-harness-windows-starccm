// Probe12.java — DEC-005 attempt 4/4 (FINAL)
// CRITICAL lead from Probe11: FvRepresentation has generateMeshReport(List) -> NeoProperty.
// The "List" likely takes FieldFunction(s). If so, NeoProperty contains per-cell Ux values.
//
// Test path: get FvRepresentation -> generateMeshReport(List<FF>) -> NeoProperty ->
// getDoubleVector("Ux") or similar -> 16641 cell-center Ux values (129*129).
// Then post-process: for each of the 17 Ghia y-points, find the cell-center nearest
// (x=0.5, y=y_i) and read Ux. Write to u_centerline.csv.
//
// This is the LAST reflective attempt before falling back to the user's 1500-line
// CliExportFieldData cascade or giving up.
import star.common.*;
import star.base.neo.*;
import java.io.*;
import java.lang.reflect.*;
import java.util.*;

public class Probe12 extends StarMacro {
    public void execute() {
        Simulation sim = getActiveSimulation();
        sim.println("=== Probe12 START ===");
        PrintWriter pw = null;
        try {
            pw = new PrintWriter(new FileWriter(
                "D:\\CFD-harness-Windows-StarCCM\\probe12_fvrep_meshreport.log"));
        } catch (Throwable t) { sim.println("can't open log: " + t); return; }
        try {
            RegionManager rm = sim.getRegionManager();
            Region reg = null;
            for (Object r : rm.getRegions()) { if (r instanceof Region) { reg = (Region) r; break; } }
            if (reg == null) { pw.println("no region"); pw.close(); return; }
            FieldFunctionManager ffm = sim.getFieldFunctionManager();
            FieldFunction velFF = ffm.getFunction("Velocity");
            FieldFunction uxFF = velFF.getComponentFunction(0);
            pw.println("velFF: " + velFF.getClass().getName());
            pw.println("uxFF: " + uxFF.getClass().getName());

            // Get FvRepresentation
            Object repMgr = sim.getClass().getMethod("getRepresentationManager").invoke(sim);
            Object reps = repMgr.getClass().getMethod("getRegionRepresentations").invoke(repMgr);
            Object fvRep = null;
            if (reps instanceof Vector) {
                for (Object r : (Vector<?>) reps) {
                    if (r.getClass().getName().contains("FvRepresentation")) { fvRep = r; break; }
                }
            }
            if (fvRep == null) { pw.println("no FvRepresentation"); pw.close(); return; }
            pw.println("fvRep: " + fvRep.getClass().getName());

            // generateMeshReport(List) — try with single uxFF
            Method genMR = fvRep.getClass().getMethod("generateMeshReport", List.class);
            pw.println("generateMeshReport: " + genMR.toString());
            List<Object> ffList = new ArrayList<>();
            ffList.add(uxFF);
            Object np = genMR.invoke(fvRep, ffList);
            pw.println("generateMeshReport -> " + (np == null ? "null" : np.getClass().getName()));
            if (np != null) {
                Object keys = null;
                try { keys = np.getClass().getMethod("getKeys").invoke(np); } catch (Throwable t) {}
                if (keys instanceof Vector) {
                    for (Object k : (Vector<?>) keys) {
                        String ks = String.valueOf(k);
                        StringBuilder row = new StringBuilder("  key=" + ks);
                        try {
                            Object dv = np.getClass().getMethod("getDouble", String.class).invoke(np, ks);
                            row.append(" double=" + dv);
                        } catch (Throwable t) { /* skip */ }
                        try {
                            Object dvv = np.getClass().getMethod("getDoubleVector", String.class).invoke(np, ks);
                            if (dvv instanceof double[]) {
                                double[] arr = (double[]) dvv;
                                row.append(" doubleVec[len=" + arr.length);
                                if (arr.length > 0) row.append(", first=" + arr[0]);
                                if (arr.length > 1) row.append(", last=" + arr[arr.length-1]);
                                row.append("]");
                            } else if (dvv != null) {
                                row.append(" doubleVec=" + dvv.getClass().getName());
                            }
                        } catch (Throwable t) { /* skip */ }
                        try {
                            Object iv = np.getClass().getMethod("getIntVector", String.class).invoke(np, ks);
                            if (iv instanceof int[]) {
                                int[] arr = (int[]) iv;
                                row.append(" intVec[len=" + arr.length + ", first=" + arr[0] + "]");
                            } else if (iv != null) {
                                row.append(" intVec=" + iv.getClass().getName());
                            }
                        } catch (Throwable t) { /* skip */ }
                        try {
                            Object ov = np.getClass().getMethod("getObjectVector", String.class, ObjectRegistry.class).invoke(np, ks, (ObjectRegistry) null);
                            if (ov != null) {
                                row.append(" objectVec=" + ov.getClass().getName() + " size=" + (ov instanceof Vector ? ((Vector<?>) ov).size() : "?"));
                            }
                        } catch (Throwable t) { /* skip */ }
                        pw.println(row.toString());
                    }
                }
                try {
                    Object ht = np.getClass().getMethod("getHashtable").invoke(np);
                    if (ht instanceof Hashtable) {
                        pw.println("--- Hashtable keys ---");
                        for (Object k : ((Hashtable<?,?>) ht).keySet()) {
                            pw.println("  ht-key: " + k + " -> " + ((Hashtable<?,?>) ht).get(k).getClass().getName());
                        }
                    }
                } catch (Throwable t) { /* skip */ }
                pw.println("--- ALL NeoProperty methods ---");
                for (Method m : np.getClass().getMethods()) {
                    StringBuilder sb = new StringBuilder("  ");
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

            // Also try getCellSetManager -> getCellSets -> each CellSet has Coordinates?
            pw.println("--- CellSetManager walk ---");
            try {
                Object csm = fvRep.getClass().getMethod("getCellSetManager").invoke(fvRep);
                if (csm != null) {
                    pw.println("csm: " + csm.getClass().getName());
                    for (Method m : csm.getClass().getMethods()) {
                        if (m.getName().contains("Cell") || m.getName().contains("Set") || m.getName().contains("Region")) {
                            StringBuilder sb = new StringBuilder("  ");
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
                }
            } catch (Throwable t) { pw.println("CellSetMgr err: " + t); }

        } catch (Throwable t) {
            pw.println("FATAL: " + t);
        }
        pw.close();
        sim.println("=== Probe12 END ===");
    }
}
