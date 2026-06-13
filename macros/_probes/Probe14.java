// Probe14.java — DEC-005 attempt 6/6 (FINAL VIABLE PATH)
// Use ffm.createFieldFunction() to make a user-defined y-coordinate
// field function, then split the cavity into 17 horizontal slabs
// using splitRegionsByFunction, then bind VolumeAverageReport(Ux)
// to each slab to get 17 average Ux values along y. This is the
// "VolumeAverageReport works (per Probe13)" + "splitRegionsByFunction
// exists (per Probe10)" combined path.
//
// User-defined FF API on 2402 R8:
//   ffm.createFieldFunction() -> UserFieldFunction
//   ff.setDefinition(String)   // STAR-CCM+ expression language
//   ff.setPresentationName(String)
// 
// We define the FF as "$Position[1]" (Y component of Position) or
// "$CoordinateY" — these are STAR-CCM+ built-in coordinate expressions.
import star.common.*;
import star.base.neo.*;
import java.io.*;
import java.lang.reflect.*;
import java.util.*;

public class Probe14 extends StarMacro {
    public void execute() {
        Simulation sim = getActiveSimulation();
        sim.println("=== Probe14 START ===");
        PrintWriter pw = null;
        try {
            pw = new PrintWriter(new FileWriter(
                "D:\\CFD-harness-Windows-StarCCM\\probe14_split_yaverage.log"));
        } catch (Throwable t) { sim.println("can't open log: " + t); return; }
        try {
            FieldFunctionManager ffm = sim.getFieldFunctionManager();
            RegionManager rm = sim.getRegionManager();
            Object repMgr = sim.getClass().getMethod("getReportManager").invoke(sim);
            Object mm = sim.getMeshManager();

            Region reg = null;
            for (Object r : rm.getRegions()) { if (r instanceof Region) { reg = (Region) r; break; } }
            if (reg == null) { pw.println("no region"); pw.close(); return; }
            FieldFunction velFF = ffm.getFunction("Velocity");
            FieldFunction uxFF = velFF.getComponentFunction(0);

            // VolumeAverageReport class
            Class<?> vaCls = null;
            for (String cn : new String[]{"star.common.VolumeAverageReport", "star.base.report.VolumeAverageReport"}) {
                try { vaCls = Class.forName(cn); } catch (ClassNotFoundException cnf) {}
            }
            if (vaCls == null) { pw.println("no VolumeAverageReport class"); pw.close(); return; }

            // Strategy 1: createFieldFunction() with $Position[1] (Y) expression
            pw.println("=== Strategy 1: user-defined FF $Position[1] ===");
            FieldFunction yFF = null;
            try {
                Object userFF = ffm.getClass().getMethod("createFieldFunction").invoke(ffm);
                pw.println("userFF class: " + userFF.getClass().getName());
                // setPresentationName
                try { userFF.getClass().getMethod("setPresentationName", String.class).invoke(userFF, "DEC005_Y_probe14"); pw.println("  setPresentationName OK"); } catch (Throwable t) { pw.println("  setPresentationName FAIL: " + t); }
                // setDefinition
                String[] exprs = {"$Position[1]", "$CoordinateY", "Position[1]", "CoordinateY", "({Position}[1])", "$Y", "Position.Y"};
                for (String e : exprs) {
                    try {
                        Method sd = userFF.getClass().getMethod("setDefinition", String.class);
                        sd.invoke(userFF, e);
                        pw.println("  setDefinition(" + e + ") OK");
                        // try to validate by reading back
                        Object gex = userFF.getClass().getMethod("getExpression").invoke(userFF);
                        pw.println("  getExpression = " + gex);
                        yFF = (FieldFunction) userFF;
                        break;
                    } catch (Throwable t) {
                        pw.println("  setDefinition(" + e + ") FAIL: " + t.getMessage());
                    }
                }
            } catch (Throwable t) {
                pw.println("createFieldFunction FAIL: " + t);
            }

            // If we have a yFF, try to split the region into 17 slabs
            if (yFF != null) {
                pw.println("=== splitRegionsByFunction with 17 thresholds ===");
                // First check region extents
                double[] ext = (double[]) mm.getClass().getMethod("getRegionExtents", Region.class).invoke(mm, reg);
                pw.println("region extents: " + (ext == null ? "null" : java.util.Arrays.toString(ext)));
                // Try previewSplitRegions first
                try {
                    Object n = mm.getClass().getMethod("previewSplitRegions", FieldFunction.class, Collection.class).invoke(mm, yFF, java.util.Collections.singletonList(reg));
                    pw.println("previewSplitRegions(Y FF) -> " + n);
                } catch (Throwable t) { pw.println("previewSplitRegions FAIL: " + t); }
            } else {
                pw.println("no yFF — fall back to plain Velocity: Magnitude split for binary 2-slab test");
                // Try split with Velocity: Magnitude (likely splits into low-vel and high-vel regions)
                FieldFunction magFF = velFF.getMagnitudeFunction();
                try {
                    Object n = mm.getClass().getMethod("previewSplitRegions", FieldFunction.class, Collection.class).invoke(mm, magFF, java.util.Collections.singletonList(reg));
                    pw.println("previewSplitRegions(magFF) -> " + n);
                } catch (Throwable t) { pw.println("previewSplitRegions(magFF) FAIL: " + t); }
            }

            // Try a 2-slab Velocity: Magnitude split (regardless of yFF success) just to see
            pw.println("=== Try splitting with Velocity: Magnitude (binary test) ===");
            FieldFunction magFF = velFF.getMagnitudeFunction();
            if (magFF != null) {
                try {
                    int nSplits = (Integer) mm.getClass().getMethod("previewSplitRegions", FieldFunction.class, Collection.class).invoke(mm, magFF, java.util.Collections.singletonList(reg));
                    pw.println("previewSplitRegions(magFF) -> " + nSplits + " regions (binary test)");
                    // Don't actually split (would mutate the .sim); just report the count
                } catch (Throwable t) { pw.println("previewSplitRegions(magFF) FAIL: " + t); }
            }

        } catch (Throwable t) {
            pw.println("FATAL: " + t);
        }
        pw.close();
        sim.println("=== Probe14 END ===");
    }
}
