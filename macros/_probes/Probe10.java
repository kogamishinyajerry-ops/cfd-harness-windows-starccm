// Probe10.java — DEC-005 attempt 2/3
// Enumerate ALL Region methods to find any path to a per-cell field
// value. Probe9 found Region has no getRepresentation() on this
// 2402 R8 build. Now check if Region itself has any direct
// value/sample/probe method, or if there's an internal Mesh-related
// method that returns InternalMesh directly. Also try getting the
// 1-cell-region path via Part (instead of SimpleBlockPart which
// doesn't exist on 2402 R8) — split the existing region via
// Y-segments.
import star.common.*;
import star.base.neo.*;
import java.io.*;
import java.lang.reflect.*;
import java.util.*;

public class Probe10 extends StarMacro {
    public void execute() {
        Simulation sim = getActiveSimulation();
        sim.println("=== Probe10 START ===");
        PrintWriter pw = null;
        try {
            pw = new PrintWriter(new FileWriter(
                "D:\\CFD-harness-Windows-StarCCM\\probe10_region_diag.log"));
        } catch (Throwable t) { sim.println("can't open log: " + t); return; }
        try {
            // 1. ALL Region methods
            RegionManager rm = sim.getRegionManager();
            Region reg = null;
            for (Object r : rm.getRegions()) {
                if (r instanceof Region) { reg = (Region) r; break; }
            }
            if (reg == null) { pw.println("no region"); pw.close(); return; }
            pw.println("Region class: " + reg.getClass().getName());
            pw.println("--- ALL Region methods ---");
            for (Method m : reg.getClass().getMethods()) {
                String n = m.getName();
                StringBuilder sb = new StringBuilder("  ");
                sb.append(n).append("(");
                Class<?>[] pts = m.getParameterTypes();
                for (int i = 0; i < pts.length; i++) {
                    if (i > 0) sb.append(", ");
                    sb.append(pts[i].getSimpleName());
                }
                sb.append(") -> ").append(m.getReturnType().getSimpleName());
                if (sb.length() < 140) pw.println(sb.toString());
            }

            // 2. Walk superclass chain
            pw.println("--- Region superclass chain ---");
            for (Class<?> c = reg.getClass().getSuperclass(); c != null && c != Object.class; c = c.getSuperclass()) {
                pw.println("  super: " + c.getName());
            }

            // 3. Try region.getMesh() (the same one probe_sol used)
            pw.println("--- getMesh attempts ---");
            for (String mn : new String[]{"getMesh", "getVolumeMesh", "getMeshObject", "getMeshManager", "getRepresentation", "getMeshRepresentation", "getInternalMesh", "getMeshFactory", "getMeshPipelineController"}) {
                try {
                    Method m = reg.getClass().getMethod(mn);
                    Object o = m.invoke(reg);
                    if (o != null) {
                        pw.println("reg." + mn + " -> " + o.getClass().getName());
                        // dump its class too
                        for (Method m2 : o.getClass().getMethods()) {
                            if (m2.getName().contains("Cell") || m2.getName().contains("Value") || m2.getName().contains("Sample") || m2.getName().contains("Point") || m2.getName().contains("Internal")) {
                                StringBuilder sb = new StringBuilder("    ");
                                sb.append(m2.getName()).append("(");
                                Class<?>[] pts = m2.getParameterTypes();
                                for (int i = 0; i < pts.length; i++) {
                                    if (i > 0) sb.append(", ");
                                    sb.append(pts[i].getSimpleName());
                                }
                                sb.append(") -> ").append(m2.getReturnType().getSimpleName());
                                if (sb.length() < 130) pw.println(sb.toString());
                            }
                        }
                    } else {
                        pw.println("reg." + mn + " -> null");
                    }
                } catch (NoSuchMethodException nsme) { pw.println("reg." + mn + " NOT FOUND"); }
                catch (Throwable t) { pw.println("reg." + mn + " err: " + t.getMessage()); }
            }

            // 4. Simulation-level mesh managers
            pw.println("--- Simulation mesh managers ---");
            for (String mn : new String[]{"getMeshManager", "getMeshFactory", "getRepresentationManager", "getMeshOperationManager"}) {
                try {
                    Method m = Simulation.class.getMethod(mn);
                    Object o = m.invoke(sim);
                    if (o != null) {
                        pw.println("sim." + mn + " -> " + o.getClass().getName());
                        for (Method m2 : o.getClass().getMethods()) {
                            if (m2.getName().contains("Cell") || m2.getName().contains("Sample") || m2.getName().contains("Point") || m2.getName().contains("Value") || m2.getName().contains("Part") || m2.getName().contains("Region")) {
                                StringBuilder sb = new StringBuilder("    ");
                                sb.append(m2.getName()).append("(");
                                Class<?>[] pts = m2.getParameterTypes();
                                for (int i = 0; i < pts.length; i++) {
                                    if (i > 0) sb.append(", ");
                                    sb.append(pts[i].getSimpleName());
                                }
                                sb.append(") -> ").append(m2.getReturnType().getSimpleName());
                                if (sb.length() < 130) pw.println(sb.toString());
                            }
                        }
                    } else {
                        pw.println("sim." + mn + " -> null");
                    }
                } catch (NoSuchMethodException nsme) { pw.println("sim." + mn + " NOT FOUND"); }
                catch (Throwable t) { pw.println("sim." + mn + " err: " + t.getMessage()); }
            }

            // 5. Try Candidate report class names via Class.forName + createReport
            pw.println("--- Report class candidates ---");
            Object repMgr = sim.getClass().getMethod("getReportManager").invoke(sim);
            pw.println("ReportManager: " + repMgr.getClass().getName());
            String[] reportCandidates = {
                "star.common.LineSampleReport",
                "star.common.LineAverageReport",
                "star.common.LineIntegralReport",
                "star.common.PointSampleReport",
                "star.common.PointReport",
                "star.common.PointProbeReport",
                "star.common.FieldFunctionReport",
                "star.common.SurfaceAverageReport",
                "star.common.SurfaceIntegralReport",
                "star.common.SurfaceReport",
                "star.common.BoundaryReport",
                "star.common.TopologyReport",
                "star.common.FieldReport",
                "star.common.ScalarReport",
                "star.common.XYReport",
                "star.common.LineReport",
                "star.common.SampleReport",
                "star.base.report.LineSampleReport",
                "star.base.report.LineAverageReport",
                "star.base.report.PointSampleReport",
                "star.base.report.XYPlotReport",
            };
            Method createReport = null;
            for (Method m : repMgr.getClass().getMethods()) {
                if (m.getName().equals("createReport") && m.getParameterTypes().length == 1) {
                    createReport = m;
                    break;
                }
            }
            if (createReport != null) {
                pw.println("createReport method: " + createReport.toString());
                for (String cn : reportCandidates) {
                    try {
                        Class<?> cls = Class.forName(cn);
                        Object rep = createReport.invoke(repMgr, cls);
                        if (rep != null) {
                            pw.println("  RESOLVED+CREATED: " + cn + " -> " + rep.getClass().getName());
                            // dump its setters
                            for (Method sm : rep.getClass().getMethods()) {
                                if (sm.getName().startsWith("set") || sm.getName().startsWith("get")) {
                                    if (sm.getName().contains("Field") || sm.getName().contains("Part") || sm.getName().contains("Sample") || sm.getName().contains("Point") || sm.getName().contains("Line") || sm.getName().contains("Coordinate") || sm.getName().contains("Direction") || sm.getName().contains("Input")) {
                                        StringBuilder sb = new StringBuilder("    ");
                                        sb.append(sm.getName()).append("(");
                                        Class<?>[] pts = sm.getParameterTypes();
                                        for (int i = 0; i < pts.length; i++) {
                                            if (i > 0) sb.append(", ");
                                            sb.append(pts[i].getSimpleName());
                                        }
                                        sb.append(") -> ").append(sm.getReturnType().getSimpleName());
                                        if (sb.length() < 130) pw.println(sb.toString());
                                    }
                                }
                            }
                            // clean up
                            try { repMgr.getClass().getMethod("removeReport", rep.getClass()).invoke(repMgr, rep); } catch (Throwable ignored) {}
                        }
                    } catch (ClassNotFoundException cnf) { pw.println("  NOT FOUND: " + cn); }
                    catch (Throwable t) { pw.println("  FAIL: " + cn + " -> " + t.getMessage()); }
                }
            }

            // 6. Try Region.getBoundaryManager().getBoundaries() — for line-sample report we need a boundary
            pw.println("--- Region boundaries ---");
            try {
                Object bm = reg.getClass().getMethod("getBoundaryManager").invoke(reg);
                if (bm != null) {
                    pw.println("boundaryMgr: " + bm.getClass().getName());
                    Method gb = bm.getClass().getMethod("getBoundaries");
                    Object bcol = gb.invoke(bm);
                    if (bcol instanceof Collection) {
                        for (Object b : (Collection<?>) bcol) {
                            pw.println("  boundary: " + b.getClass().getSimpleName() + " type=" + b.getClass().getMethod("getBoundaryType").invoke(b).getClass().getSimpleName());
                        }
                    }
                }
            } catch (Throwable t) { pw.println("boundaryMgr err: " + t); }

        } catch (Throwable t) {
            pw.println("FATAL: " + t);
        }
        pw.close();
        sim.println("=== Probe10 END ===");
    }
}
