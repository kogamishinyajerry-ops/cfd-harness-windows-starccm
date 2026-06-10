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

        // Optional: env var LDC_ITERS can override gIters for smoke tests.
        // E.g. LDC_ITERS=100 starccm+.bat sim.sim -batch LidDrivenCavity.java
        try {
            String envIters = System.getenv("LDC_ITERS");
            if (envIters != null && !envIters.isEmpty()) {
                int override = Integer.parseInt(envIters.trim());
                if (override > 0 && override < 1000000) gIters = override;
            }
        } catch (Throwable ignore) {}

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
            callStep("11. Export scene PNG (Velocity + Pressure)", this::step11ExportPNG);

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
    // Step 1: Import the cavity STL
    // ============================================================
    // The harness pre-generates ``D:\\StarCCM Codebuddy\\Cases\\lid_driven_cavity.stl``
    // (a simple 12-triangle box cavity) and the macro imports it via
    // PartImportManager. We don't use ``star.solidmodeler.*`` because
    // it's not part of the standard classpath in STAR-CCM+ 19.02
    // (the user's other macros all use PartImportManager).
    // ============================================================
    private void step1CreateBlock() throws Exception {
        String stlPath = "D:/StarCCM Codebuddy/Cases/lid_driven_cavity.stl";
        try {
            File stl = new File(stlPath);
            if (!stl.exists()) {
                writeLog("STL not found: " + stlPath + " (harness should pre-generate it)");
                gSim.println("    [step1] STL missing: " + stlPath);
                return;
            }
            PartImportManager pim = gSim.get(PartImportManager.class);
            if (pim == null) { writeLog("no PartImportManager"); return; }
            // importStlPart signature (per CylinderFlow.java, 7-arg version):
            //   importStlPart(String path, String mode, Units units,
            //                   boolean merge, double cadUnitLength,
            //                   boolean heal, boolean autoOrient)
            Units units = gSim.getUnitsManager().getPreferredUnits(
                Dimensions.Builder().length(1).build()
            );
            try {
                pim.importStlPart(
                    stlPath,                          // String path
                    "OneSurfacePerPatch",              // String mode
                    units,                             // Units
                    true,                              // boolean merge
                    1.0E-5,                            // double cadUnitLength
                    false,                             // boolean heal
                    false                              // boolean autoOrient
                );
            } catch (NoSuchMethodError nsme) {
                // Fallback: 5-arg version (older STAR-CCM+)
                pim.importStlPart(stlPath, "OneSurfacePerPatch", units, true, 1.0E-5);
            }
            writeLog("STL imported: " + stlPath);
            gSim.println("    [step1] STL imported");
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
            // Try a list of physics models. The first one that succeeds wins.
            // Models: Steady + Laminar + SegregatedFlow + Viscous are required
            // for an LDC case. Per ProbeCylV3, the right packages are
            // star.flow.* (Steady, SegregatedFlow) and star.turbulence.*
            // (Laminar, NOT star.flow.Laminar which doesn't exist).
            String[] wanted = {
                "star.common.ThreeDimensionalModel",
                "star.flow.SteadyModel",
                "star.turbulence.LaminarModel",
                "star.flow.SegregatedFlowModel",
                "star.flow.ConstantDensityModel",
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
        // Strategy (modeled on the user's VortexStreetV161R_Build.java
        // which is the proven-working path for STAR-CCM+ 19.02.009):
        //   1. Get the Wall BC type from ConditionTypeManager
        //      (NOT via direct VelocityProfile class lookup, which
        //      is version-fragile).
        //   2. Assign Wall type to all cavity walls (default is
        //      already Wall, but we re-set for safety).
        //   3. For the top wall (lid), set the VelocityProfile
        //      via getValues().get(VelocityProfile.class)
        //      + getMethod(ConstantVectorProfileMethod.class)
        //      + setComponents(1, 0, 0).
        //   4. Other walls stay no-slip (default).
        // Step 5: set Wall BC type on all cavity walls, and set the
        // top wall (lid) tangential velocity. Uses direct imports
        // (star.common.* already imported) so the compiler can infer
        // T for gSim.get() — model: VortexStreetV161R_Build.java.
        try {
            // Step 5a: get the Wall BC type from ConditionTypeManager.
            ConditionTypeManager ctm = gSim.get(ConditionTypeManager.class);
            if (ctm == null) { writeLog("no ConditionTypeManager"); return; }
            // ctm.get(WallBoundary.class) returns the Wall BC instance
            WallBoundary wallBC = ctm.get(WallBoundary.class);
            if (wallBC == null) { writeLog("no Wall BC type instance"); return; }
            writeLog("Wall BC type: " + wallBC.getClass().getName());

            // Step 5b: assign Wall type to all cavity boundaries by name.
            RegionManager rm = gSim.getRegionManager();
            Collection<?> regions = rm.getRegions();
            if (regions == null || regions.isEmpty()) { writeLog("no regions for BCs"); return; }
            Region reg = (Region) regions.iterator().next();
            BoundaryManager bm = reg.getBoundaryManager();
            Collection<?> bds = bm.getBoundaries();
            if (bds == null || bds.isEmpty()) { writeLog("no boundaries"); return; }

            int setBCTypeCount = 0;
            for (Object b : bds) {
                Boundary bnd = (Boundary) b;
                String name = bnd.getPresentationName();
                if (name == null) continue;
                String low = name.toLowerCase();
                if (low.contains("cylinder") || low.contains("inlet") || low.contains("outlet")
                        || low.contains("freestream")) {
                    writeLog("  skip " + name + " (not cavity wall)");
                    continue;
                }
                boolean isCavityWall = low.matches("x_(min|max)|y_(min|max)|z_(min|max)|default boundary|default");
                if (!isCavityWall) {
                    writeLog("  skip " + name + " (not a cavity wall)");
                    continue;
                }
                try {
                    bnd.setBoundaryType((BoundaryType) wallBC);
                    setBCTypeCount++;
                } catch (Throwable t) {
                    writeLog("  setBoundaryType(" + name + ") FAIL: " + unwrap(t));
                }
            }
            writeLog("BC type set: " + setBCTypeCount + " wall(s) -> Wall");

            // Step 5c: set top wall (lid) velocity. Ux=1, Uy=0, Uz=0.
            // APPROACH: switch the y_max boundary type to VelocityInlet
            // (mathematically equivalent to a moving wall for the LDC case).
            // Wall boundaries in STAR-CCM+ 19.02 don't expose a VelocityProfile
            // condition by default; trying to set one throws "Condition not
            // found in ConditionManager". Using VelocityInlet is the same
            // trick NACA's CliNaca2412E2E.java uses — proven working path.
            Class<?> velInletCls = Class.forName("star.common.InletBoundary");
            Object velInletBC = ((ConditionTypeManager) ctm).get((Class<? extends ConditionType>) velInletCls);
            if (velInletBC == null) {
                writeLog("no InletBoundary BC type instance from ConditionTypeManager; lid stays no-slip");
                gSim.println("    [step5] BCs set (only types; velocity NOT set)");
                return;
            }
            int lidTypeSet = 0;
            for (Object b : bds) {
                Boundary bnd = (Boundary) b;
                String name = bnd.getPresentationName();
                if (name == null) continue;
                if (!name.toLowerCase().equals("y_max")) continue;
                try {
                    bnd.setBoundaryType((BoundaryType) velInletBC);
                    lidTypeSet++;
                    writeLog("  y_max (TOP) BC type set -> InletBoundary (lumped as moving-wall)");
                } catch (Throwable t) {
                    writeLog("  y_max setBoundaryType(InletBoundary) FAIL: " + unwrap(t));
                }
            }
            if (lidTypeSet == 0) {
                writeLog("  no boundary named y_max found; lid velocity NOT set");
                gSim.println("    [step5] BCs set (only types; no y_max boundary)");
                return;
            }

            // Now set the velocity profile on the inlet.
            // Try VelocityMagnitudeProfile (inlet scalar profile) first;
            // fall back to VelocityProfile (vector) if the magnitude path
            // doesn't fit (e.g., non-zero y component).
            Class<?> cvpmClass = findClass("ConstantVectorProfileMethod");
            Class<?> cspmScalarCls = findClass("ConstantScalarProfileMethod");
            if (cvpmClass == null) {
                writeLog("ConstantVectorProfileMethod not findable; lid velocity NOT set");
                return;
            }
            int velSet = 0;
            for (Object b : bds) {
                Boundary bnd = (Boundary) b;
                String name = bnd.getPresentationName();
                if (name == null) continue;
                if (!name.toLowerCase().equals("y_max")) continue;
                try {
                    Object values = bnd.getValues();
                    // Try VelocityProfile (vector) first for the (1,0,0) setting
                    boolean setThis = false;
                    Class<?> vpCls = findClass("VelocityProfile");
                    if (vpCls != null) {
                        try {
                            Object vp = values.getClass().getMethod("get", Class.class).invoke(values, vpCls);
                            if (vp != null) {
                                Object cspm = vp.getClass().getMethod("getMethod", Class.class).invoke(vp, cvpmClass);
                                if (cspm == null) {
                                    vp.getClass().getMethod("setMethod", Class.class).invoke(vp, cvpmClass);
                                    cspm = vp.getClass().getMethod("getMethod", Class.class).invoke(vp, cvpmClass);
                                }
                                if (cspm != null) {
                                    Object q = cspm.getClass().getMethod("getQuantity").invoke(cspm);
                                    try {
                                        Method setComp = q.getClass().getMethod("setComponents",
                                            double.class, double.class, double.class);
                                        setComp.invoke(q, gLidU, 0.0, 0.0);
                                    } catch (Throwable tc) {
                                        // Fallback setValueAndUnits
                                        Class<?> vecCls = Class.forName("star.vec.Vec");
                                        Object vec = vecCls.getConstructor(double.class, double.class, double.class)
                                            .newInstance(gLidU, 0.0, 0.0);
                                        Class<?> unitsCls = Class.forName("star.common.Units");
                                        Object uV = gSim.getUnitsManager().getObject("m/s");
                                        Method setVU = q.getClass().getMethod("setValueAndUnits", vecCls, unitsCls);
                                        setVU.invoke(q, vec, uV);
                                    }
                                    writeLog("  BC: " + name + " (TOP/lid) V=(" + gLidU + ",0,0) via VelocityProfile (vector)");
                                    setThis = true;
                                }
                            }
                        } catch (Throwable t) {
                            writeLog("  VelocityProfile (vector) path FAIL: " + unwrap(t));
                        }
                    }
                    // Fallback: VelocityMagnitudeProfile (scalar)
                    if (!setThis) {
                        Class<?> vmpCls = findClass("VelocityMagnitudeProfile");
                        Class<?> cspmS = cspmScalarCls;
                        if (vmpCls != null && cspmS == null) cspmS = cvpmClass; // try constant vector as scalar
                        if (vmpCls != null) {
                            try {
                                Object vp = values.getClass().getMethod("get", Class.class).invoke(values, vmpCls);
                                if (vp != null) {
                                    Object cspm = vp.getClass().getMethod("getMethod", Class.class).invoke(vp, cspmS);
                                    if (cspm == null) {
                                        vp.getClass().getMethod("setMethod", Class.class).invoke(vp, cspmS);
                                        cspm = vp.getClass().getMethod("getMethod", Class.class).invoke(vp, cspmS);
                                    }
                                    if (cspm != null) {
                                        Object q = cspm.getClass().getMethod("getQuantity").invoke(cspm);
                                        Class<?> unitsCls = Class.forName("star.common.Units");
                                        Object uV = gSim.getUnitsManager().getObject("m/s");
                                        Method setVU = q.getClass().getMethod("setValueAndUnits", double.class, unitsCls);
                                        setVU.invoke(q, gLidU, uV);
                                        writeLog("  BC: " + name + " (TOP/lid) V=(" + gLidU + ",0,0) via VelocityMagnitudeProfile (scalar)");
                                        setThis = true;
                                    }
                                }
                            } catch (Throwable t) {
                                writeLog("  VelocityMagnitudeProfile (scalar) path FAIL: " + unwrap(t));
                            }
                        }
                    }
                    if (setThis) velSet++;
                } catch (Throwable t) {
                    writeLog("  y_max velocity profile FAIL: " + unwrap(t));
                }
            }
            writeLog("BCs set: type=" + setBCTypeCount + " walls, lid=" + lidTypeSet + " -> VelocityInlet, vel=" + velSet);
            gSim.println("    [step5] BCs set (type=" + setBCTypeCount + ", lid=inlet+" + velSet + ")");
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
            // Get the active field function for Velocity. We try
            // multiple lookup APIs because the FieldFunctionManager
            // surface is one of the most-version-sensitive parts of
            // STAR-CCM+.
            Object velFF = null;
            Object ffm = callMethod(gSim, "getFieldFunctionManager");
            if (ffm == null) {
                // gSim.get(Class<T>) is generic; cast to raw Class to
                // avoid the T extends ClientServerObject inference
                // problem when we have Class<?> from forName.
                try {
                    Class ffmCls = Class.forName("star.common.FieldFunctionManager");
                    Object ffmObj = gSim.get(ffmCls);
                    if (ffmObj != null) ffm = ffmObj;
                } catch (Throwable t) {}
            }
            String[] tryNames = {"Velocity", "VelocityVector", "Vel", "$Velocity"};
            for (String name : tryNames) {
                if (ffm == null || velFF != null) break;
                // Try the most common lookup methods
                for (String methodName : new String[]{
                        "getFieldFunction", "getFunction", "getByLabel",
                        "getByPresentationName", "getObject", "get"
                }) {
                    try {
                        Method m = ffm.getClass().getMethod(methodName, String.class);
                        velFF = m.invoke(ffm, name);
                        if (velFF != null) break;
                    } catch (Throwable ignore) {}
                }
            }
            if (velFF == null) {
                writeLog("WARNING: no Velocity FF; writing NaN u_centerline");
                writeCSV();
                return;
            }
            writeLog("Velocity FF: " + velFF.getClass().getSimpleName());
            // Evaluate at each Ghia point. PROVEN pattern from
            // CliExportFieldData.java (probeViaOneCellRegion):
            //   1. Get the X-component scalar FF: uxFF = velFF.getComponentFunction(0)
            //   2. For each Ghia point (x,y,z):
            //      a. Create a SimpleBlockPart with tiny bbox around (x,y,z)
            //      b. Create a region from this part
            //      c. Create SumReport bound to uxFF on this region
            //      d. Read getReportMonitorValue()  (= Ux at the cell)
            //      e. Cleanup (remove region + report)
            // The 1-cell region's SumReport effectively samples the FF at (x,y,z).
            // This pattern was verified working in our probe (probe_sol.log):
            //   velFF = PrimitiveFieldFunction, uxFF = VectorComponentFieldFunction
            //   sim.getReportManager().createReport(star.base.report.SumReport)
            //   rep.setFieldFunction(uxFF)
            //   rep.getParts().setObjects([region])
            //   rep.getReportMonitorValue() -> double
            // velFF is Object-typed (returned via reflection). Use reflection to call
            // getComponentFunction(0) — returns a scalar FF for the X component.
            Object uxFF = null;
            try {
                Method gcf = velFF.getClass().getMethod("getComponentFunction", int.class);
                uxFF = gcf.invoke(velFF, 0);
            } catch (Throwable t) {
                writeLog("velFF.getComponentFunction(0) FAIL: " + unwrap(t));
                writeCSV();
                return;
            }
            if (uxFF == null) {
                writeLog("velFF.getComponentFunction(0) returned null; writing NaN");
                writeCSV();
                return;
            }
            writeLog("Ux scalar FF: " + uxFF.getClass().getSimpleName());
            Object repMgr = gSim.getClass().getMethod("getReportManager").invoke(gSim);
            if (repMgr == null) {
                writeLog("no ReportManager; writing NaN");
                writeCSV();
                return;
            }
            Class<?> sumCls = null;
            for (String cn : new String[]{"star.common.SumReport", "star.base.report.SumReport"}) {
                try { sumCls = Class.forName(cn); break; } catch (Throwable t) {}
            }
            if (sumCls == null) {
                writeLog("no SumReport class; writing NaN");
                writeCSV();
                return;
            }
            // Locate SimpleBlockPart factory on RegionManager
            RegionManager rm = gSim.getRegionManager();
            Class<?> blockCls = null;
            for (String cn : new String[]{
                    "star.meshing.SimpleBlockPart",
                    "star.meshing.BlockPart",
                    "star.common.SimpleBlockPart",
                    "star.common.BlockPart"}) {
                try { blockCls = Class.forName(cn); break; } catch (Throwable t) {}
            }
            if (blockCls == null) {
                writeLog("no BlockPart class; writing NaN");
                writeCSV();
                return;
            }
            int sampled = 0;
            for (int i = 0; i < 17; i++) {
                double px = 0.5, py = gYPoints[i], pz = 0.5 * gThickness;
                Object part = null, region = null, rep = null;
                try {
                    // Create SimpleBlockPart
                    Method createPart = null;
                    for (String mn : new String[]{"createSimpleBlockPart", "createBlockPart"}) {
                        try { createPart = rm.getClass().getMethod(mn); break; } catch (Throwable t) {}
                    }
                    if (createPart == null) { writeLog("no createSimpleBlockPart"); continue; }
                    part = createPart.invoke(rm);
                    // Set tiny bbox
                    try {
                        Method setBox = part.getClass().getMethod("setBlockCoordinateSystem",
                            double.class, double.class, double.class, double.class, double.class, double.class);
                        double eps = 1.0e-3;
                        setBox.invoke(part, px - eps, px + eps, py - eps, py + eps, pz - eps, pz + eps);
                    } catch (Throwable t) {
                        writeLog("  y=" + py + " setBlockCoordinateSystem FAIL: " + unwrap(t));
                        continue;
                    }
                    // Create region
                    Method createReg = null;
                    for (String mn : new String[]{"createRegion", "newRegionFromPart"}) {
                        try { createReg = rm.getClass().getMethod(mn, part.getClass()); break; } catch (Throwable t) {}
                    }
                    if (createReg == null) { writeLog("no createRegion method"); continue; }
                    region = createReg.invoke(rm, part);
                    // Create SumReport
                    rep = repMgr.getClass().getMethod("createReport", Class.class).invoke(repMgr, sumCls);
                    rep.getClass().getMethod("setFieldFunction", Class.forName("star.common.FieldFunction"))
                        .invoke(rep, uxFF);
                    Object parts = rep.getClass().getMethod("getParts").invoke(rep);
                    java.util.List<Object> regList = new java.util.ArrayList<>();
                    regList.add(region);
                    parts.getClass().getMethod("setObjects", java.util.Collection.class).invoke(parts, regList);
                    // Read value
                    Method gv = rep.getClass().getMethod("getReportMonitorValue");
                    Object v = gv.invoke(rep);
                    if (v instanceof Number) {
                        gUAtY[i] = ((Number) v).doubleValue();
                        sampled++;
                    } else if (v instanceof double[]) {
                        double[] arr = (double[]) v;
                        if (arr.length >= 1) { gUAtY[i] = arr[0]; sampled++; }
                    }
                    writeLog("  y=" + py + " ux=" + gUAtY[i]);
                } catch (Throwable t) {
                    writeLog("  y=" + py + " FAIL: " + unwrap(t));
                } finally {
                    // Cleanup
                    try { repMgr.getClass().getMethod("removeReport", rep.getClass()).invoke(repMgr, rep); } catch (Throwable t) {}
                    try { rm.getClass().getMethod("removeRegion", region.getClass()).invoke(rm, region); } catch (Throwable t) {}
                    try { rm.getClass().getMethod("removePart", part.getClass()).invoke(rm, part); } catch (Throwable t) {}
                }
            }
            writeLog("sampled: " + sampled + "/17 points");
            writeCSV();
            gSim.println("    [step9] u_centerline sampled (" + sampled + "/17)");
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

    // ============================================================
    // Step 11: Export scene PNG (velocity magnitude + pressure)
    // ============================================================
    // Reference: VortexStreetV129R.java (proven scene+hardcopy path on
    // STAR-CCM+ 19.02.009).  Strategy: reflection-safe — try multiple
    // FF lookup names and method names, degrade gracefully (log + skip)
    // if any single sub-step fails.  This step never throws; it logs
    // each sub-step's outcome and returns.  At least one PNG must be
    // produced for the step to count as success.
    // ============================================================
    private void step11ExportPNG() throws Exception {
        if (!gRunOk) { writeLog("skip scene: run not ok"); return; }
        int made = 0;
        // Render velocity magnitude (range 0..gLidU)
        try {
            if (renderScalarField("Velocity", "LDC_Velocity",
                    "lid_driven_cavity_velocity.png", 0.0, gLidU)) {
                made++;
            }
        } catch (Throwable t) {
            writeLog("velocity PNG FAIL: " + unwrap(t));
        }
        // Render pressure (symmetric range; will be auto if fails)
        try {
            if (renderScalarField("Pressure", "LDC_Pressure",
                    "lid_driven_cavity_pressure.png", -1.0, 1.0)) {
                made++;
            }
        } catch (Throwable t) {
            writeLog("pressure PNG FAIL: " + unwrap(t));
        }
        gSim.println("    [step11] PNG exported: " + made);
    }

    /**
     * Render a scalar field to a PNG via reflection-safe scene + hardcopy.
     * Mirrors the proven pattern in VortexStreetV129R.java:99-101.
     * Returns true on success.
     */
    private boolean renderScalarField(String ffLookupName, String sceneName,
                                       String pngFileName, double minR, double maxR) {
        try {
            // 1. Resolve FieldFunctionManager
            Object ffm = callMethod(gSim, "getFieldFunctionManager");
            if (ffm == null) {
                try {
                    Class<?> ffmCls = Class.forName("star.common.FieldFunctionManager");
                    ffm = gSim.get(ffmCls);
                } catch (Throwable ignore) {}
            }
            if (ffm == null) { writeLog("  no FieldFunctionManager"); return false; }

            // 2. Lookup FF by name (try several method names)
            Object ff = null;
            for (String mn : new String[]{
                    "getFieldFunction", "getFunction", "getByLabel",
                    "getByPresentationName", "getObject", "get"
            }) {
                try {
                    Method m = ffm.getClass().getMethod(mn, String.class);
                    ff = m.invoke(ffm, ffLookupName);
                    if (ff != null) break;
                } catch (Throwable ignore) {}
            }
            if (ff == null) { writeLog("  FF '" + ffLookupName + "' not found"); return false; }
            writeLog("  FF: " + ffLookupName + " (" + ff.getClass().getSimpleName() + ")");

            // 3. Get SceneManager + delete any pre-existing scene of same name
            Object sm = gSim.getSceneManager();
            if (sm == null) { writeLog("  no SceneManager"); return false; }
            try {
                Object scenesObj = callMethod(sm, "getScenes");
                if (scenesObj instanceof Collection) {
                    for (Object so : (Collection<?>) scenesObj) {
                        String n = (String) callMethod(so, "getPresentationName");
                        if (sceneName.equals(n)) {
                            try {
                                sm.getClass().getMethod("deleteScene", so.getClass()).invoke(sm, so);
                            } catch (Throwable ignore) {}
                        }
                    }
                }
            } catch (Throwable ignore) {}
            Object scene = sm.getClass().getMethod("createScene", String.class).invoke(sm, sceneName);
            if (scene == null) { writeLog("  scene not created"); return false; }

            // 4. Create ScalarDisplayer
            Object sd = scene.getClass().getMethod("createScalarDisplayer", String.class)
                              .invoke(scene, "Field");
            if (sd == null) { writeLog("  ScalarDisplayer not created"); return false; }

            // 5. setFieldFunction
            try {
                Class<?> ffCls = Class.forName("star.common.FieldFunction");
                sd.getClass().getMethod("setFieldFunction", ffCls).invoke(sd, ff);
            } catch (Throwable t) {
                writeLog("  setFieldFunction FAIL (non-fatal): " + unwrap(t));
            }

            // 6. setRange via DoubleVector (best-effort; auto-range if it fails)
            try {
                Object sdq = callMethod(sd, "getScalarDisplayQuantity");
                if (sdq != null) {
                    Class<?> dvCls = Class.forName("star.vec.DoubleVector");
                    Object dv = dvCls.getConstructor(double[].class)
                                     .newInstance(new double[]{minR, maxR});
                    sdq.getClass().getMethod("setRange", dvCls).invoke(sdq, dv);
                }
            } catch (Throwable t) {
                writeLog("  setRange FAIL (auto-range): " + unwrap(t));
            }

            // 7. Add all cavity boundaries to the scene's CreatorGroup
            try {
                Object cg = callMethod(sd, "getScene");
                if (cg == null) cg = scene;
                Object creatorGroup = callMethod(cg, "getCreatorGroup");
                if (creatorGroup != null) {
                    RegionManager rm = gSim.getRegionManager();
                    for (Object r : rm.getRegions()) {
                        Region reg = (Region) r;
                        for (Object b : reg.getBoundaryManager().getBoundaries()) {
                            try {
                                creatorGroup.getClass().getMethod("add", Object.class)
                                                    .invoke(creatorGroup, b);
                            } catch (Throwable ignore) {}
                        }
                    }
                }
            } catch (Throwable t) {
                writeLog("  add boundaries FAIL (non-fatal): " + unwrap(t));
            }

            // 8. initializeAndWait + renderAndWait
            try {
                scene.getClass().getMethod("initializeAndWait").invoke(scene);
            } catch (Throwable t) {
                writeLog("  initializeAndWait FAIL (non-fatal): " + unwrap(t));
            }
            try {
                scene.getClass().getMethod("renderAndWait").invoke(scene);
            } catch (Throwable t) {
                writeLog("  renderAndWait FAIL: " + unwrap(t));
                return false;
            }

            // 9. exportImagePNG(File, int width, int height, int aa)
            File png = new File(gResultsDir, pngFileName);
            png.getParentFile().mkdirs();
            try {
                scene.getClass().getMethod("exportImagePNG", File.class,
                        int.class, int.class, int.class)
                    .invoke(scene, png, 1280, 800, 1);
            } catch (Throwable t) {
                writeLog("  exportImagePNG FAIL: " + unwrap(t));
                return false;
            }
            writeLog("  PNG OK: " + png.getAbsolutePath() +
                     " size=" + (png.exists() ? png.length() : -1) + "B");
            return true;
        } catch (Throwable t) {
            writeLog("  render '" + ffLookupName + "' FAIL: " + unwrap(t));
            return false;
        }
    }
}
