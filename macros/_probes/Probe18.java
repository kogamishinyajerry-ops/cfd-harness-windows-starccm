// Probe18.java — SurfaceAverageReport per boundary (last viable path)
// Per Probe10, the cavity has 9 boundaries: 8 WallBoundary + 1 InletBoundary (lid).
// SurfaceAverageReport on each gives the average Ux on that boundary.
// For a 2D LDC, this gives 4 "wall" Ux values that constrain the field shape.
import star.common.*;
import star.base.neo.*;
import java.io.*;
import java.lang.reflect.*;
import java.util.*;

public class Probe18 extends StarMacro {
    public void execute() {
        Simulation sim = getActiveSimulation();
        sim.println("=== Probe18 START ===");
        PrintWriter pw = null;
        try {
            pw = new PrintWriter(new FileWriter(
                "D:\\CFD-harness-Windows-StarCCM\\probe18_surface_avg.log"));
        } catch (Throwable t) { sim.println("can't open log: " + t); return; }
        try {
            FieldFunctionManager ffm = sim.getFieldFunctionManager();
            RegionManager rm = sim.getRegionManager();
            Object repMgr = sim.getClass().getMethod("getReportManager").invoke(sim);
            Region reg = null;
            for (Object r : rm.getRegions()) { if (r instanceof Region) { reg = (Region) r; break; } }
            FieldFunction velFF = ffm.getFunction("Velocity");
            FieldFunction uxFF = velFF.getComponentFunction(0);
            FieldFunction magFF = velFF.getMagnitudeFunction();

            // Find SurfaceAverageReport class
            Class<?> saCls = null;
            for (String cn : new String[]{
                "star.common.SurfaceAverageReport", "star.common.AreaAverageReport",
                "star.base.report.SurfaceAverageReport", "star.base.report.AreaAverageReport",
                "star.common.SurfaceReport", "star.base.report.SurfaceReport",
                "star.common.BoundaryReport", "star.base.report.BoundaryReport",
                "star.common.SurfaceIntegralReport", "star.base.report.SurfaceIntegralReport",
                "star.common.IntegralReport", "star.base.report.IntegralReport"}) {
                try { saCls = Class.forName(cn); pw.println("resolved: " + cn); break; } catch (ClassNotFoundException cnf) {}
            }
            if (saCls == null) { pw.println("no surface report class"); pw.close(); return; }

            // Iterate all boundaries, get Ux + Ux mag for each
            Object bm = reg.getClass().getMethod("getBoundaryManager").invoke(reg);
            Object bcol = bm.getClass().getMethod("getBoundaries").invoke(bm);
            pw.println("=== SurfaceAverageReport per boundary ===");
            for (Object b : (Collection<?>) bcol) {
                Boundary bnd = (Boundary) b;
                String bType = bnd.getBoundaryType().getClass().getSimpleName();
                String bName = bnd.getPresentationName();
                pw.println("--- boundary: " + bName + " type=" + bType);
                for (FieldFunction ff : new FieldFunction[]{uxFF, magFF}) {
                    try {
                        Object rep = repMgr.getClass().getMethod("createReport", Class.class).invoke(repMgr, saCls);
                        rep.getClass().getMethod("setPresentationName", String.class).invoke(rep, "probe18_" + bName + "_" + ff.getPresentationName());
                        rep.getClass().getMethod("setFieldFunction", FieldFunction.class).invoke(rep, ff);
                        List<Object> bList = new ArrayList<>(); bList.add(bnd);
                        Object parts = rep.getClass().getMethod("getParts").invoke(rep);
                        parts.getClass().getMethod("setObjects", Collection.class).invoke(parts, bList);
                        Object v = rep.getClass().getMethod("getReportMonitorValue").invoke(rep);
                        pw.println("    " + ff.getPresentationName() + ": " + v);
                        try { repMgr.getClass().getMethod("removeReport", rep.getClass()).invoke(repMgr, rep); } catch (Throwable t) {}
                    } catch (Throwable t) {
                        pw.println("    " + ff.getPresentationName() + " FAIL: " + t.getMessage());
                    }
                }
            }

        } catch (Throwable t) {
            pw.println("FATAL: " + t);
        }
        pw.close();
        sim.println("=== Probe18 END ===");
    }
}
