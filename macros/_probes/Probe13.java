// Probe13.java — DEC-005 attempt 5/5 (NEW STRATEGY)
// Use sim.getMeshManager().splitRegionsByFunction(FF, regions) to split
// the cavity region into N horizontal slabs (by Velocity: Magnitude or
// Y-coordinate), then bind VolumeAverageReport to each slab to get
// the average Ux per slab. This gives N Ux values along y.
//
// The splitRegionsByFunction takes a FieldFunction and returns nothing
// (it modifies the region in-place). The split happens along iso-contour
// bands of the field function value. To split by Y, we need an
// auxiliary field that increases linearly with Y — could use the
// Y-coordinate field function, but we don't know if that exists in 2402 R8.
// 
// Alternative: a USER-DEFINED field function `y_position` defined as
// `{CoordinateY}` — STAR-CCM+ has {CoordinateX}, {CoordinateY}, {CoordinateZ}
// as built-in scalar FFs. Let's try that.
import star.common.*;
import star.base.neo.*;
import java.io.*;
import java.lang.reflect.*;
import java.util.*;

public class Probe13 extends StarMacro {
    public void execute() {
        Simulation sim = getActiveSimulation();
        sim.println("=== Probe13 START ===");
        PrintWriter pw = null;
        try {
            pw = new PrintWriter(new FileWriter(
                "D:\\CFD-harness-Windows-StarCCM\\probe13_split_ffaverage.log"));
        } catch (Throwable t) { sim.println("can't open log: " + t); return; }
        try {
            FieldFunctionManager ffm = sim.getFieldFunctionManager();
            // Try to find a "Coordinate" or "Position" field function
            pw.println("=== Find a Y-coordinate scalar field function ===");
            String[] coordFFs = {"CoordinateY", "Position Y", "Y", "$PositionY", "${CoordinateY}", "PointCoordinateY", "Position[1]"};
            FieldFunction yFF = null;
            for (String n : coordFFs) {
                try {
                    FieldFunction f = ffm.getFunction(n);
                    if (f != null) { pw.println("  FOUND: " + n + " -> " + f.getClass().getName()); yFF = f; break; }
                } catch (Throwable t) { /* skip */ }
            }
            if (yFF == null) {
                // try via getObject (sentinel-aware)
                for (String n : coordFFs) {
                    try {
                        Object f = ffm.getClass().getMethod("getObject", String.class).invoke(ffm, n);
                        if (f instanceof FieldFunction) { pw.println("  FOUND via getObject: " + n); yFF = (FieldFunction) f; break; }
                    } catch (Throwable t) { /* skip */ }
                }
            }
            if (yFF == null) {
                // scan the entire pool
                try {
                    Object all = ffm.getClass().getMethod("getObjects").invoke(ffm);
                    if (all instanceof Collection) {
                        for (Object f : (Collection<?>) all) {
                            if (f instanceof FieldFunction) {
                                String pn = ((FieldFunction) f).getPresentationName();
                                if (pn != null && (pn.toLowerCase().contains("coord") || pn.toLowerCase().contains("position"))) {
                                    pw.println("  pool: " + pn + " -> " + f.getClass().getSimpleName());
                                }
                            }
                        }
                    }
                } catch (Throwable t) { pw.println("pool scan err: " + t); }
                pw.println("  no Y-coordinate FF found; trying VolumeAverageReport path directly on the existing region instead");
            }

            // Direct path: just call VolumeAverageReport on the cavity region for Ux
            pw.println("=== VolumeAverageReport(Ux) on cavity region ===");
            RegionManager rm = sim.getRegionManager();
            Region reg = null;
            for (Object r : rm.getRegions()) { if (r instanceof Region) { reg = (Region) r; break; } }
            if (reg == null) { pw.println("no region"); pw.close(); return; }
            FieldFunction velFF = ffm.getFunction("Velocity");
            FieldFunction uxFF = velFF.getComponentFunction(0);
            pw.println("reg: " + reg.getClass().getName());
            pw.println("uxFF: " + uxFF.getClass().getName());

            Object repMgr = sim.getClass().getMethod("getReportManager").invoke(sim);
            Class<?> vaCls = null;
            for (String cn : new String[]{
                "star.common.VolumeAverageReport", "star.common.AverageReport",
                "star.common.FieldAverageReport", "star.common.MeanReport",
                "star.base.report.VolumeAverageReport", "star.base.report.AverageReport",
                "star.base.report.FieldAverageReport", "star.base.report.MeanReport"}) {
                try { vaCls = Class.forName(cn); pw.println("  resolved: " + cn); break; } catch (ClassNotFoundException cnf) {}
            }
            if (vaCls == null) { pw.println("no avg report class"); pw.close(); return; }
            Object avgRep = repMgr.getClass().getMethod("createReport", Class.class).invoke(repMgr, vaCls);
            pw.println("avgRep: " + avgRep.getClass().getName());
            try { avgRep.getClass().getMethod("setPresentationName", String.class).invoke(avgRep, "DEC005_probe13_ux_avg"); } catch (Throwable t) {}
            try { avgRep.getClass().getMethod("setFieldFunction", FieldFunction.class).invoke(avgRep, uxFF); pw.println("  setFieldFunction OK"); } catch (Throwable t) { pw.println("  setFieldFunction FAIL: " + t); }
            try {
                Object parts = avgRep.getClass().getMethod("getParts").invoke(avgRep);
                List<Object> regList = new ArrayList<>(); regList.add(reg);
                parts.getClass().getMethod("setObjects", Collection.class).invoke(parts, regList);
                pw.println("  setParts OK");
            } catch (Throwable t) { pw.println("  setParts FAIL: " + t); }
            // Read value
            try {
                Method gv = avgRep.getClass().getMethod("getReportMonitorValue");
                Object v = gv.invoke(avgRep);
                pw.println("  getReportMonitorValue: " + v + " class=" + (v == null ? "null" : v.getClass().getName()));
            } catch (Throwable t) { pw.println("  getReportMonitorValue FAIL: " + t); }
            try {
                Object v = avgRep.getClass().getMethod("getValue").invoke(avgRep);
                pw.println("  getValue: " + v);
            } catch (Throwable t) { pw.println("  getValue FAIL: " + t); }

            // Clean up
            try { repMgr.getClass().getMethod("removeReport", avgRep.getClass()).invoke(repMgr, avgRep); } catch (Throwable t) {}

            // Also try MeshManager.getRegionExtents(reg) to confirm region is 0..1 in y
            pw.println("=== Region extents (via MeshManager.getRegionExtents) ===");
            try {
                Object mm = sim.getMeshManager();
                double[] ext = (double[]) mm.getClass().getMethod("getRegionExtents", Region.class).invoke(mm, reg);
                pw.println("extents: " + (ext == null ? "null" : java.util.Arrays.toString(ext)));
            } catch (Throwable t) { pw.println("getRegionExtents FAIL: " + t); }

        } catch (Throwable t) {
            pw.println("FATAL: " + t);
        }
        pw.close();
        sim.println("=== Probe13 END ===");
    }
}
