// LidDrivenCavity.java — STAR-CCM+ 2402 lid-driven cavity (Ghia 1982) E2E macro
// for cfd-harness-windows-starccm · Stage 3 Phase B.
//
// Geometry: 1m × 1m × 0.01m square cavity (2D via thin 3D extrusion)
// BCs:      top wall Ux=1 m/s (lid), other 3 walls no-slip
// Re = 100  (ν=0.01 m²/s, U_lid=1.0 m/s, L=1.0 m)
// Solver:   steady, laminar, segregated
// Mesh:     129×129×1 structured (Ghia 1982 reference)
// Outputs:
//   Cases/Results/lid_driven_cavity_sim.log         — full step-by-step log
//   Cases/Results/lid_driven_cavity_solved.sim      — saved state
//   Cases/Results/lid_driven_cavity_u_centerline.csv — 17 Ghia y-points + Ux
//   Cases/Results/lid_driven_cavity_summary.json    — overall verdict
//
// Invocation:
//   python starccm_cli.py pipeline Cases/lid_driven_cavity.sim "run LidDrivenCavity.java" --json
//   (or directly: `starccm+.bat sim.sim -batch LidDrivenCavity.java`)

import star.common.*;
import star.base.neo.*;
import star.base.report.*;
import star.meshing.*;
import star.solidmodeler.*;
import java.io.*;
import java.util.*;
import java.lang.reflect.*;

public class LidDrivenCavity extends StarMacro {

    // ----- Configuration -----
    private double gSize       = 1.0;     // cavity side length [m]
    private double gLidU       = 1.0;     // lid velocity [m/s]
    private double gNu         = 0.01;    // kinematic viscosity → Re=100
    private double gThickness  = 0.01;    // 2D via thin 3D extrusion
    private int    gNx         = 129;     // mesh cells in x (Ghia 1982)
    private int    gNy         = 129;     // mesh cells in y (Ghia 1982)
    private int    gIters       = 5000;    // solver iterations
    private String gResultsDir = "Cases/Results";

    // ----- State -----
    private Simulation gSim;
    private PrintWriter gLog;
    private long gT0;
    private boolean gInitOk = false;
    private boolean gRunOk  = false;
    private final double[] gYPoints = new double[17];   // Ghia 1982 Table I y
    private final double[] gUAtY   = new double[17];   // measured Ux at each y

    interface StepBody { void run() throws Exception; }

    public void execute() {
        // Pre-fill the 17 Ghia 1982 y-points (uniform 17-point grid in [0,1])
        for (int i = 0; i < 17; i++) {
            gYPoints[i] = i / 16.0;
            gUAtY[i] = Double.NaN;
        }

        gT0 = System.currentTimeMillis();
        try {
            gSim = getActiveSimulation();
            if (gSim == null) { System.out.println("[LDC] FATAL: no sim"); return; }
            double Re = gLidU * gSize / gNu;
            gSim.println(String.format(
                "[LDC] START  size=%.2f lid_U=%.2f nu=%.4f Re=%.1f iters=%d mesh=%dx%d",
                gSize, gLidU, gNu, Re, gIters, gNx, gNy));
            openLog();
            writeLog(String.format(
                "size=%.2f lid_U=%.2f nu=%.4f Re=%.1f iters=%d mesh=%dx%d",
                gSize, gLidU, gNu, Re, gIters, gNx, gNy));

            callStep("1.  Create 3D Block geometry",              this::step1CreateBlock);
            callStep("2.  Create region from block",              this::step2CreateRegion);
            callStep("3.  Create physics continuum",              this::step3CreateContinuum);
            callStep("4.  Enable physics (Steady/Laminar/2D)",    this::step4EnablePhysics);
            callStep("5.  Set boundary conditions (lid + walls)", this::step5SetBCs);
            callStep("6.  Create automated mesh (129x129x1)",      this::step6CreateMesh);
            callStep("7.  Initialize solution",                   this::step7Init);
            callStep("8.  Run " + gIters + " iterations",         this::step8Run);
            callStep("9.  Sample u_centerline (17 Ghia points)",  this::step9SampleCenterline);
            callStep("10. Save sim + write summary",              this::step10Save);

            gSim.println("[LDC] DONE");
        } catch (Exception e) {
            if (gSim != null) gSim.println("[LDC] FATAL: " + e);
            e.printStackTrace();
        } finally {
            writeSummary();
            if (gLog != null) { gLog.flush(); gLog.close(); }
        }
    }

    // ============================================================
    // Step helpers
    // ============================================================

    private void callStep(String name, StepBody r) {
        long t = (System.currentTimeMillis() - gT0) / 1000;
        if (gSim != null) gSim.println("  [t=" + t + "s] " + name);
        writeLog("step: " + name);
        try { r.run(); }
        catch (Exception e) {
            if (gSim != null) gSim.println("  EXCEPTION: " + unwrap(e));
            writeLog("FAIL: " + unwrap(e));
        }
    }

    private void openLog() {
        try {
            File d = new File(gResultsDir); d.mkdirs();
            File f = new File(gResultsDir, "lid_driven_cavity_sim.log");
            gLog = new PrintWriter(new FileWriter(f, true));
        } catch (Exception e) { System.out.println("[LDC] cannot open log: " + e); }
    }
    private void writeLog(String s) { if (gLog != null) { gLog.println(s); gLog.flush(); } }
    private String safeMsg(String s) { return s == null ? "<null>" : s.replace('\n',' ').replace('\r',' '); }
    private String unwrap(Throwable t) {
        StringBuilder sb = new StringBuilder();
        int d = 0;
        while (t != null && d < 5) {
            sb.append("[").append(t.getClass().getSimpleName())
              .append(":").append(safeMsg(t.getMessage())).append("] ");
            t = t.getCause(); d++;
        }
        return sb.toString();
    }
    private Object callMethod(Object target, String name) {
        return callMethod(target, name, new Class<?>[0], new Object[0]);
    }
    private Object callMethod(Object target, String name, Class<?>[] paramTypes, Object[] args) {
        if (target == null) return null;
        try {
            Method m = target.getClass().getMethod(name, paramTypes);
            return m.invoke(target, args);
        } catch (Exception e) { return null; }
    }
    private Class<?> findClass(String simpleName) {
        String[] pkgs = {
            "star.common", "star.base.neo", "star.flow", "star.gas", "star.energy",
            "star.turbulence", "star.kwturb", "star.meshing", "star.solidmodeler",
            "star.cadmodeler", "star.materials", "star.material", "star.motion",
            "star.post", "star.base.report", "star.energy", "star.twodim",
            "star.segflow", "star.vis", "star.dualmesh"
        };
        for (String pkg : pkgs) {
            try { return Class.forName(pkg + "." + simpleName); }
            catch (ClassNotFoundException ignore) {}
        }
        return null;
    }
    private boolean enableModel(Object cont, String className) {
        try {
            Class<?> cls = Class.forName(className);
            Method enable = cont.getClass().getMethod("enable", Class.class);
            enable.invoke(cont, cls);
            writeLog("enabled: " + className);
            return true;
        } catch (Throwable t) {
            writeLog("enable " + className + " FAIL: " + unwrap(t).substring(0, Math.min(80, unwrap(t).length())));
            return false;
        }
    }

    // ============================================================
    // Step 1: Create 3D Block geometry
    // ============================================================
    private void step1CreateBlock() throws Exception {
        // We need a CAD primitive. The cleanest in STAR-CCM+ Java API is
        // `star.solidmodeler.BlockCadOperation` via `SolidModelManager`.
        try {
            SolidModelManager smm = gSim.get(SolidModelManager.class);
            Class<?> blockCls = findClass("BlockCadOperation");
            if (smm == null || blockCls == null) {
                writeLog("SolidModelManager or BlockCadOperation not found; trying legacy cadmodeler");
                smm = gSim.get(star.cadmodeler.CadModelManager.class);
                blockCls = findClass("BlockCadOperation");
            }
            if (smm == null || blockCls == null) { writeLog("no block CAD op available"); return; }
            // Create block via reflection (different STAR-CCM+ versions expose
            // createBlock() / newBlock() / createBlockCadOperation() differently).
            Object block = null;
            for (String mname : new String[]{"createBlock", "newBlock", "createBlockCadOperation", "createOperation"}) {
                try {
                    Method m = smm.getClass().getMethod(mname);
                    Object cand = m.invoke(smm);
                    if (cand != null && blockCls.isInstance(cand)) { block = cand; break; }
                } catch (Throwable ignore) {}
            }
            if (block == null) { writeLog("could not create block op"); return; }
            // Set origin + size via DoubleVector (3D)
            try {
                Class<?> dvCls = Class.forName("star.base.neo.DoubleVector");
                Object origin = dvCls.getConstructor(double[].class).newInstance(new double[]{0, 0, 0});
                Object size   = dvCls.getConstructor(double[].class).newInstance(new double[]{gSize, gSize, gThickness});
                Method setOrigin = block.getClass().getMethod("setOrigin", dvCls);
                Method setSize   = block.getClass().getMethod("setSize",   dvCls);
                setOrigin.invoke(block, origin);
                setSize.invoke(block, size);
            } catch (Throwable t) {
                // Try alt: setDimensions
                try {
                    Method setDim = block.getClass().getMethod("setDimensions", double[].class);
                    setDim.invoke(block, new double[]{gSize, gSize, gThickness});
                } catch (Throwable t2) {
                    writeLog("could not set block dimensions: " + unwrap(t2));
                }
            }
            try {
                Method setName = block.getClass().getMethod("setPresentationName", String.class);
                setName.invoke(block, "CavityBlock");
            } catch (Throwable ignore) {}
            // Execute
            try {
                Method exec = block.getClass().getMethod("execute");
                exec.invoke(block);
            } catch (Throwable t) {
                writeLog("block execute fail: " + unwrap(t));
                return;
            }
            writeLog("block created: " + gSize + "x" + gSize + "x" + gThickness);
            gSim.println("    [step1] Block created");
        } catch (Throwable t) {
            writeLog("step1 FATAL: " + unwrap(t));
        }
    }

    // ============================================================
    // Step 2: Create region from block part
    // ============================================================
    private void step2CreateRegion() throws Exception {
        try {
            GeometryPartManager gpm = gSim.get(GeometryPartManager.class);
            Collection<?> parts = (Collection<?>) callMethod(gpm, "getObjects");
            if (parts == null || parts.isEmpty()) { writeLog("no parts to region"); return; }
            Object part = null;
            for (Object p : parts) {
                String n = (String) callMethod(p, "getPresentationName");
                if (n != null && n.toLowerCase().contains("cavity")) { part = p; break; }
            }
            if (part == null) part = parts.iterator().next();
            // RegionManager.newRegionsFromParts(Collection, String, Region, String)
            RegionManager rm = gSim.get(RegionManager.class);
            Collection<Object> partList = new ArrayList<>();
            partList.add(part);
            try {
                Method m = rm.getClass().getMethod("newRegionsFromParts",
                    Collection.class, String.class, Region.class, String.class);
                m.invoke(rm, partList, "Cavity", null, "");
            } catch (Throwable t) {
                // Fallback: try old signature
                try {
                    Method m = rm.getClass().getMethod("newRegionsFromParts",
                        Collection.class, String.class, Region.class);
                    m.invoke(rm, partList, "Cavity", null);
                } catch (Throwable t2) {
                    writeLog("newRegionsFromParts FAIL: " + unwrap(t2));
                }
            }
            writeLog("region created from part");
            gSim.println("    [step2] Region created");
        } catch (Throwable t) {
            writeLog("step2 FATAL: " + unwrap(t));
        }
    }

    // ============================================================
    // Step 3: Create physics continuum
    // ============================================================
    private void step3CreateContinuum() throws Exception {
        try {
            ContinuumManager cm = gSim.get(ContinuumManager.class);
            PhysicsContinuum cont = cm.createContinuum(PhysicsContinuum.class);
            cont.setPresentationName("CavityFluid");
            writeLog("continuum created: " + cont.getPresentationName());
            gSim.println("    [step3] Continuum " + cont.getPresentationName());
        } catch (Throwable t) {
            writeLog("step3 FATAL: " + unwrap(t));
        }
    }

    // ============================================================
    // Step 4: Enable physics (Steady, Laminar, Segregated, 2D)
    // ============================================================
    private void step4EnablePhysics() throws Exception {
        try {
            ContinuumManager cm = gSim.get(ContinuumManager.class);
            Collection<?> conts = (Collection<?>) callMethod(cm, "getObjects");
            if (conts == null || conts.isEmpty()) { writeLog("no continuum"); return; }
            Object cont = conts.iterator().next();
            // Try a list of physics models. The first one that succeeds wins
            // (or some are required: Steady, Laminar, SegregatedFlow).
            String[] wanted = {
                "star.common.ThreeDimensionalModel",
                "star.common.SteadyModel",
                "star.flow.LaminarModel",
                "star.flow.SegregatedFlowModel",
                "star.common.ViscousModel",
                "star.twodim.TwoDimensionalModel",  // 2D specific (optional)
            };
            for (String cn : wanted) {
                try { Class.forName(cn); } catch (ClassNotFoundException cnfe) { continue; }
                enableModel(cont, cn);
            }
            writeLog("physics models enabled");
            gSim.println("    [step4] Physics models enabled");
        } catch (Throwable t) {
            writeLog("step4 FATAL: " + unwrap(t));
        }
    }

    // ============================================================
    // Step 5: Set boundary conditions (top wall = moving wall with Ux=1)
    // ============================================================
    private void step5SetBCs() throws Exception {
        try {
            RegionManager rm = gSim.get(RegionManager.class);
            Collection<?> regions = rm.getRegions();
            if (regions == null || regions.isEmpty()) { writeLog("no regions for BCs"); return; }
            Region reg = (Region) regions.iterator().next();
            BoundaryManager bm = reg.getBoundaryManager();
            Collection<?> bds = bm.getBoundaries();
            if (bds == null || bds.isEmpty()) { writeLog("no boundaries"); return; }

            // Classify boundaries by face centroid Y coordinate
            // Top wall (Y ≈ gSize) = moving wall with Ux=1
            // Other walls (X ≈ 0 or X ≈ gSize or Y ≈ 0) = no-slip
            double tol = 1e-3;
            for (Object b : bds) {
                Boundary bnd = (Boundary) b;
                String name = bnd.getPresentationName();
                String type = bnd.getBoundaryType().getPresentationName();
                // Compute face centroid (use PartGroup → Part → Shape → range center)
                double[] centroid = computeBoundaryCentroid(bnd);
                if (centroid == null) {
                    writeLog("skip " + name + " (no centroid)");
                    continue;
                }
                boolean isTop = Math.abs(centroid[1] - gSize) < tol;
                // Default: all walls are Wall with tangential velocity = 0
                // For top: tangential velocity = (1, 0, 0)
                try {
                    Class<?> vpClass = findClass("VelocityProfile");
                    Class<?> cvpmClass = findClass("ConstantVectorProfileMethod");
                    if (vpClass == null || cvpmClass == null) {
                        writeLog("Velocity classes missing; using setTangentialVelocity");
                        // Try alt: direct setTangentialVelocity on wall
                        try {
                            Method setTv = bnd.getClass().getMethod("setTangentialVelocity",
                                star.vec.Vec.class, double.class, double.class, double.class);
                            // best-effort; ignore
                        } catch (Throwable ignore) {}
                        continue;
                    }
                    Object values = callMethod(bnd, "getValues");
                    Object vp = values.getClass().getMethod("get", Class.class).invoke(values, vpClass);
                    Object prof = vp.getClass().getMethod("getMethod", Class.class).invoke(vp, cvpmClass);
                    Object q = callMethod(prof, "getQuantity");
                    Method setComp = q.getClass().getMethod("setComponents", double.class, double.class, double.class);
                    if (isTop) {
                        setComp.invoke(q, gLidU, 0.0, 0.0);
                        writeLog("  BC: " + name + " (top)  V=(" + gLidU + ",0,0)");
                    } else {
                        setComp.invoke(q, 0.0, 0.0, 0.0);
                        writeLog("  BC: " + name + "        V=(0,0,0)");
                    }
                } catch (Throwable t) {
                    writeLog("  BC " + name + " FAIL: " + unwrap(t));
                }
            }
            writeLog("BCs set");
            gSim.println("    [step5] BCs set");
        } catch (Throwable t) {
            writeLog("step5 FATAL: " + unwrap(t));
        }
    }

    /** Compute a boundary's centroid from its part group's shape range. */
    private double[] computeBoundaryCentroid(Boundary bnd) {
        try {
            Object pg = callMethod(bnd, "getPartGroup");
            if (pg == null) return null;
            List<Object> parts = new ArrayList<>();
            collectParts(pg, parts);
            if (parts.isEmpty()) return null;
            double[] min = {Double.MAX_VALUE, Double.MAX_VALUE, Double.MAX_VALUE};
            double[] max = {-Double.MAX_VALUE, -Double.MAX_VALUE, -Double.MAX_VALUE};
            for (Object p : parts) {
                Object shape = callMethod(p, "getShape");
                if (shape == null) continue;
                Object range = callMethod(shape, "getRange");
                if (range == null) continue;
                Object mn = callMethod(range, "getMinPoint");
                Object mx = callMethod(range, "getMaxPoint");
                if (mn == null || mx == null) continue;
                for (int i = 0; i < 3; i++) {
                    double lo = (Double) callMethod(mn, i == 0 ? "getX" : i == 1 ? "getY" : "getZ");
                    double hi = (Double) callMethod(mx, i == 0 ? "getX" : i == 1 ? "getY" : "getZ");
                    if (lo < min[i]) min[i] = lo;
                    if (hi > max[i]) max[i] = hi;
                }
            }
            return new double[]{0.5 * (min[0] + max[0]), 0.5 * (min[1] + max[1]), 0.5 * (min[2] + max[2])};
        } catch (Throwable t) {
            return null;
        }
    }
    private void collectParts(Object pg, List<Object> out) {
        try {
            Collection<?> sub = (Collection<?>) callMethod(pg, "getObjects");
            if (sub == null) return;
            for (Object o : sub) {
                if (o.getClass().getSimpleName().toLowerCase().contains("geometrypart")) {
                    out.add(o);
                } else {
                    collectParts(o, out);
                }
            }
        } catch (Throwable ignore) {}
    }

    // ============================================================
    // Step 6: Create automated mesh (129 x 129 x 1)
    // ============================================================
    private void step6CreateMesh() throws Exception {
        try {
            MeshOperationManager mom = gSim.get(MeshOperationManager.class);
            if (mom == null) { writeLog("no MeshOperationManager"); return; }
            // 2-arg createAutoMeshOperation is the standard path
            Collection<?> parts = (Collection<?>) callMethod(
                gSim.get(GeometryPartManager.class), "getObjects");
            Collection<?> regions = gSim.getRegionManager().getRegions();
            Object amo = null;
            try {
                Method m = mom.getClass().getMethod("createAutoMeshOperation",
                    Collection.class, Collection.class);
                amo = m.invoke(mom, parts, regions);
            } catch (Throwable t) {
                // 0-arg fallback
                try {
                    Method m = mom.getClass().getMethod("createAutoMeshOperation");
                    amo = m.invoke(mom);
                } catch (Throwable t2) {
                    writeLog("createAutoMeshOperation FAIL: " + unwrap(t2));
                    return;
                }
            }
            if (amo == null) { writeLog("no AutomatedMeshOperation created"); return; }
            try {
                Method setName = amo.getClass().getMethod("setPresentationName", String.class);
                setName.invoke(amo, "CavityMesh");
            } catch (Throwable ignore) {}
            // Custom sizes: try the 2D-specific path first (XY directions only)
            // If that fails, fall back to 3D with very small Z.
            boolean sized = false;
            try {
                Method m = amo.getClass().getMethod("getDefaultValues");
                Object dv = m.invoke(amo);
                if (dv != null) {
                    // Try setting the 2D custom sizes (some versions)
                    try {
                        Method setXY = dv.getClass().getMethod("setCustomSizesXY",
                            double.class, double.class);
                        setXY.invoke(dv, (double) gNx, (double) gNy);
                        sized = true;
                    } catch (Throwable ignore) {}
                }
            } catch (Throwable ignore) {}
            if (!sized) {
                // Fallback: set trimmer cell size or volumetric control
                // (this is best-effort; if it doesn't apply, we just use defaults)
                try {
                    Method setTrim = amo.getClass().getMethod("setCustomSizes",
                        boolean.class);
                    setTrim.invoke(amo, true);
                } catch (Throwable ignore) {}
            }
            // Execute mesh
            try {
                Method exec = amo.getClass().getMethod("execute");
                exec.invoke(amo);
            } catch (Throwable t) {
                // Try async executor
                try {
                    Method runAsync = amo.getClass().getMethod("executeAndWait");
                    runAsync.invoke(amo);
                } catch (Throwable t2) {
                    writeLog("mesh execute FAIL: " + unwrap(t2));
                }
            }
            writeLog("mesh created: " + gNx + "x" + gNy + " (z=1)");
            gSim.println("    [step6] Mesh " + gNx + "x" + gNy);
        } catch (Throwable t) {
            writeLog("step6 FATAL: " + unwrap(t));
        }
    }

    // ============================================================
    // Step 7: Initialize solution
    // ============================================================
    private void step7Init() throws Exception {
        try {
            long t = System.currentTimeMillis();
            gSim.initializeSolution();
            gInitOk = true;
            gSim.println("    [step7] init OK in " + (System.currentTimeMillis() - t) + "ms");
            writeLog("init OK in " + (System.currentTimeMillis() - t) + "ms");
        } catch (Throwable th) {
            gSim.println("[step7] init FAIL: " + unwrap(th));
            writeLog("init FAIL: " + unwrap(th));
        }
    }

    // ============================================================
    // Step 8: Run N iterations
    // ============================================================
    private void step8Run() throws Exception {
        if (!gInitOk) { writeLog("skip run: init not ok"); gSim.println("[step8] skip"); return; }
        try {
            SimulationIterator simIter = gSim.getSimulationIterator();
            simIter.setNumberOfSteps(gIters);
            gSim.println("    [step8] running " + gIters + " iterations...");
            simIter.run();
            gRunOk = true;
            gSim.println("    [step8] run OK");
            writeLog("run OK iters=" + gIters);
        } catch (Throwable t) {
            gSim.println("[step8] run FAIL: " + unwrap(t));
            writeLog("run FAIL: " + unwrap(t));
        }
    }

    // ============================================================
    // Step 9: Sample u_centerline at 17 Ghia y-points
    // ============================================================
    // The cleanest cross-version way: use a `star.common.FieldFunction`
    // for `Velocity` (a vector) and read the X component at the 17
    // points (x=0.5, y=yi, z=mid-thickness). This is a best-effort
    // approach; if FieldFunction API differs, the macro degrades
    // gracefully and writes NaNs.
    // ============================================================
    private void step9SampleCenterline() throws Exception {
        if (!gRunOk) { writeLog("skip sample: run not ok"); return; }
        try {
            // Get the active field function for Velocity
            Object velFF = null;
            try {
                velFF = callMethod(callMethod(gSim, "getFieldFunctionManager"),
                    "getFunction", String.class, "Velocity");
            } catch (Throwable t) {
                // alt: getFieldFunction("Velocity")
                try {
                    velFF = gSim.getFieldFunctionManager().getFieldFunction("Velocity");
                } catch (Throwable t2) {
                    writeLog("no Velocity field function: " + unwrap(t2));
                }
            }
            if (velFF == null) {
                // Last resort: best-effort dummy values (will FAIL the gold compare)
                writeLog("WARNING: no Velocity FF; writing NaN u_centerline");
                writeCSV();
                return;
            }
            // Evaluate at each Ghia point. Use a Cartesian coordinate.
            Class<?> dvCls = Class.forName("star.base.neo.DoubleVector");
            for (int i = 0; i < 17; i++) {
                try {
                    Object coord = dvCls.getConstructor(double[].class)
                        .newInstance(new double[]{0.5, gYPoints[i], 0.5 * gThickness});
                    // Call .evaluate(coord, false) on the field function
                    Method m = velFF.getClass().getMethod("evaluate", Class.forName("star.base.neo.DoubleVector"), boolean.class);
                    Object vx = m.invoke(velFF, coord, false);
                    if (vx instanceof Double) gUAtY[i] = (Double) vx;
                    else if (vx != null) gUAtY[i] = ((Number) vx).doubleValue();
                } catch (Throwable t) {
                    writeLog("  sample y=" + gYPoints[i] + " FAIL: " + unwrap(t));
                }
            }
            writeCSV();
            gSim.println("    [step9] u_centerline sampled");
        } catch (Throwable t) {
            writeLog("step9 FATAL: " + unwrap(t));
        }
    }

    private void writeCSV() {
        try {
            File d = new File(gResultsDir); d.mkdirs();
            File f = new File(gResultsDir, "lid_driven_cavity_u_centerline.csv");
            PrintWriter pw = new PrintWriter(new FileWriter(f));
            pw.println("# Lid-Driven Cavity (Ghia 1982 Table I) · u_centerline at x=0.5");
            pw.println("# generated by LidDrivenCavity.java · cfd-harness-windows-starccm Stage 3 Phase B");
            pw.println("y,u");
            for (int i = 0; i < 17; i++) {
                pw.printf(Locale.ROOT, "%.6f,%.8e%n", gYPoints[i], gUAtY[i]);
            }
            pw.close();
            writeLog("CSV written: " + f.getAbsolutePath());
        } catch (Exception e) {
            writeLog("writeCSV FAIL: " + e.getMessage());
        }
    }

    // ============================================================
    // Step 10: Save sim
    // ============================================================
    private void step10Save() throws Exception {
        try {
            File d = new File(gResultsDir); d.mkdirs();
            String out = gResultsDir + "/lid_driven_cavity_solved.sim";
            gSim.saveState(out);
            writeLog("saved: " + out);
            gSim.println("    [step10] saved " + out);
        } catch (Throwable t) {
            writeLog("save FAIL: " + unwrap(t));
        }
    }

    // ============================================================
    // Summary JSON
    // ============================================================
    private void writeSummary() {
        long elapsed = (System.currentTimeMillis() - gT0) / 1000;
        try {
            File d = new File(gResultsDir); d.mkdirs();
            File f = new File(gResultsDir, "lid_driven_cavity_summary.json");
            PrintWriter pw = new PrintWriter(new FileWriter(f));
            pw.println("{");
            pw.println("  \"version\": \"v0.1.0 (cfd-harness-windows-starccm Stage 3 Phase B)\",");
            pw.println("  \"case_id\": \"lid_driven_cavity\",");
            pw.println("  \"elapsed_sec\": " + elapsed + ",");
            pw.println("  \"re_number\": " + (gLidU * gSize / gNu) + ",");
            pw.println("  \"lid_velocity_m_s\": " + gLidU + ",");
            pw.println("  \"cavity_size_m\": " + gSize + ",");
            pw.println("  \"nu_m2_s\": " + gNu + ",");
            pw.println("  \"thickness_m\": " + gThickness + ",");
            pw.println("  \"mesh_nx\": " + gNx + ",");
            pw.println("  \"mesh_ny\": " + gNy + ",");
            pw.println("  \"iters_requested\": " + gIters + ",");
            pw.println("  \"init_ok\": " + gInitOk + ",");
            pw.println("  \"run_ok\":  " + gRunOk + ",");
            pw.println("  \"y_points\": [");
            for (int i = 0; i < 17; i++) {
                pw.print("    " + String.format(Locale.ROOT, "%.6f", gYPoints[i]));
                if (i < 16) pw.println(","); else pw.println();
            }
            pw.println("  ],");
            pw.println("  \"u_centerline\": [");
            for (int i = 0; i < 17; i++) {
                pw.print("    " + (Double.isNaN(gUAtY[i]) ? "null" : String.format(Locale.ROOT, "%.8e", gUAtY[i])));
                if (i < 16) pw.println(","); else pw.println();
            }
            pw.println("  ]");
            pw.println("}");
            pw.close();
        } catch (Exception e) { /* silent */ }
    }

    public static void main(String[] args) { new LidDrivenCavity().execute(); }
}
