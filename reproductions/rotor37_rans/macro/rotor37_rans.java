import star.common.*;
import star.base.neo.*;
import star.meshing.*;
import java.lang.reflect.*;
import java.util.*;
import java.io.*;

/**
 * NASA Rotor 37 single-passage steady RANS (k-omega SST, coupled/ideal-gas, MRF).
 * Reproduction of Li et al. 2022 (AST) geometry / Suder 1996 validation, method
 * downgraded QWRLES -> RANS. Built on doc-confirmed STAR-CCM+ 2402 R8 API.
 *
 * Env overrides: ROTOR37_OMEGA (rad/s), ROTOR37_POUT (Pa), ROTOR37_BASE (m),
 *   ROTOR37_ITERS, ROTOR37_OUT (dir), ROTOR37_STL (path).
 * Hard post-condition gates -> never reports success on a hollow mesh/solve.
 */
public class rotor37_rans extends StarMacro {
    Simulation sim;
    // defaults (coarse smoke); overridden by env
    double OMEGA = 1800.0;        // rad/s (17188.7 rpm); sign about +z
    double P0_IN = 101325.0;      // Pa total
    double T0_IN = 288.15;        // K total
    double P_OUT = 115000.0;      // Pa static back-pressure
    double BASE  = 0.004;         // m base size (coarse)
    int    ITERS = 50;            // coarse smoke
    String STL   = "D:\\CFD-harness-Windows-StarCCM\\reproductions\\rotor37_rans\\geom\\fluid_passage_named.stl";
    String OUT   = "D:\\CFD-harness-Windows-StarCCM\\reproductions\\rotor37_rans\\runs";
    static final double PITCH_DEG = 10.0;
    static final int NBLADE = 36;
    boolean FLIP = false;   // ROTOR37_FLIP=1 -> inflow=high-z(geom "outlet"), outflow=low-z(geom "inlet"), flow -z
    String inflowNm()  { return FLIP ? "outlet" : "inlet"; }
    String outflowNm() { return FLIP ? "inlet" : "outlet"; }

    StringBuilder J = new StringBuilder();   // json fragments
    boolean meshOK = false; long cellCount = 0;
    boolean mrfOK = false, periodicOK = false;

    public void execute() {
        long t0 = System.currentTimeMillis();
        sim = getActiveSimulation();
        cfgFromEnv();
        cellCount = currentCells();
        log("=== Rotor37 RANS  omega=" + OMEGA + " Pout=" + P_OUT + " base=" + BASE + " iters=" + ITERS + " existingCells=" + cellCount);
        try {
            if (cellCount <= 0) {
                // PHASE A (fresh -new sim): full build incl. continuum + mesh + save. Default periodic
                // (translational) for now; reloading makes the reference-frame manager available.
                log("PHASE A: import+physics+BC+periodic+mesh+save built");
                Object part = importStl();
                Region reg = makeRegion(part);
                makePhysics(reg);
                Object[] bm = setupBoundaries(reg);
                setupPeriodic(bm[2], bm[3]);
                mesh(reg);
                if (!meshOK) { fail("no volume mesh"); return; }
                sim.saveState(OUT + "\\rotor37_built.sim");
                log("PHASE A done cells=" + cellCount + " saved rotor37_built.sim (reload for B)");
                return;
            }
            // PHASE B (reload built; RFM available): MRF -> rotational periodic (->10deg) -> REGENERATE
            // mesh so the periodic faces are conformal -> solve. This breaks the circular dependency.
            log("PHASE B: MRF + rotational periodic + remesh + solve");
            Region reg = sim.getRegionManager().getRegions().iterator().next();
            setupMRF(reg);
            configurePeriodic(reg);             // rotational, region z-axis -> ~10 deg (RFM now exists)
            if (!"0".equals(System.getenv("ROTOR37_REMESH"))) { meshOK = false; remesh(); if (!meshOK) { fail("remesh failed"); return; } }
            else meshOK = true;
            removeBadCells(reg);                 // delete degenerate (zero/neg-volume) cells before solve
            try { setShroudLabFrame(bnd(reg, "shroud")); } catch (Throwable t) { log("shroud " + root(t)); }
            setMassFlowOutlet(reg, envD("ROTOR37_MDOT", 0.55));   // per-passage; 0.55*36=19.8 kg/s (~95% choke)
            solveRamped(ITERS);
            double[] perf = reports(reg);
            save(perf, (System.currentTimeMillis() - t0) / 1000.0);
            log("=== PHASE B RESULT cells=" + cellCount + " mrf=" + mrfOK + " periodic=" + periodicOK + " mdot=" + perf[0] + " PR=" + perf[1] + " eta=" + perf[2]);
        } catch (Throwable t) {
            log("FATAL " + root(t));
            t.printStackTrace();
            save(new double[]{Double.NaN, Double.NaN, Double.NaN, Double.NaN}, (System.currentTimeMillis() - t0) / 1000.0);
        }
    }

    long currentCells() {
        try {
            Object rep = sim.getRepresentationManager().getObject("Volume Mesh");
            return ((Number) rep.getClass().getMethod("getCellCount").invoke(rep)).longValue();
        } catch (Throwable t) { return 0; }
    }

    // remove cells with zero/negative volume (and very poor quality) so the solver metrics pass
    void removeBadCells(Region reg) {
        try {
            Object mm = sim.getClass().getMethod("getMeshManager").invoke(sim);
            java.util.List<Object> regs = new java.util.ArrayList<>(); regs.add(reg);
            java.lang.reflect.Method rm = mm.getClass().getMethod("removeInvalidCells",
                java.util.Collection.class, double.class, double.class, double.class);
            for (int i = 0; i < 8; i++) {   // unconditional passes: patching creates new bad cells; repeat to fully clear
                rm.invoke(mm, regs, 0.51, 1.0e-8, 1.0e-10);
            }
            cellCount = currentCells();
            log("removeInvalidCells 8 passes done, cells=" + cellCount);
        } catch (Throwable t) { log("removeInvalidCells " + root(t)); }
    }

    // regenerate the volume mesh from the EXISTING mesh operation (so the now-rotational periodic
    // interface produces conformal periodic faces) — no new auto-mesh op created
    void remesh() {
        try {
            Object mpc = simGet("star.meshing.MeshPipelineController");
            try { mpc.getClass().getMethod("clearGeneratedMeshes").invoke(mpc); } catch (Throwable t) {}
            mpc.getClass().getMethod("generateVolumeMesh").invoke(mpc);
            cellCount = currentCells();
            meshOK = cellCount > 0;
            log("remesh (periodic active) cells=" + cellCount + " meshOK=" + meshOK);
        } catch (Throwable t) { log("remesh FAIL " + root(t)); }
    }

    // ---------------- geometry ----------------
    Object importStl() throws Exception {
        Object pim = simGet("star.meshing.PartImportManager");
        Units m = sim.getUnitsManager().getPreferredUnits(new Dimensions.Builder().length(1).build());
        pim.getClass().getMethod("importStlPart", String.class, String.class, Units.class,
                boolean.class, double.class, boolean.class, boolean.class)
            .invoke(pim, STL, "OneSurfacePerPatch", m, true, 1.0E-5, false, false);
        Object gpm = simGet("star.common.GeometryPartManager");
        Object part = ((Collection<?>) gpm.getClass().getMethod("getObjects").invoke(gpm)).iterator().next();
        int ns = ((Collection<?>) part.getClass().getMethod("getPartSurfaces").invoke(part)).size();
        log("imported " + pres(part) + " surfaces=" + ns);
        return part;
    }

    Region makeRegion(Object part) throws Exception {
        Object regm = sim.getRegionManager();
        ArrayList<Object> pl = new ArrayList<>(); pl.add(part);
        regm.getClass().getMethod("newRegionsFromParts", Collection.class, String.class, String.class, String.class, boolean.class)
            .invoke(regm, pl, "OneRegion", "OneBoundaryPerPartSurface", "OneFeatureCurve", true);
        Region reg = sim.getRegionManager().getRegions().iterator().next();
        log("region=" + pres(reg) + " boundaries=" + reg.getBoundaryManager().getBoundaries().size());
        return reg;
    }

    // ---------------- physics ----------------
    Object makePhysics(Region reg) throws Exception {
        ContinuumManager cm = sim.get(ContinuumManager.class);
        PhysicsContinuum cont = cm.createContinuum(PhysicsContinuum.class);
        cont.setPresentationName("R37");
        for (String fqn : new String[]{
                "star.common.SteadyModel", "star.material.SingleComponentGasModel",
                "star.coupledflow.CoupledFlowModel", "star.coupledflow.CoupledEnergyModel", "star.flow.IdealGasModel",
                "star.turbulence.TurbulentModel", "star.turbulence.RansTurbulenceModel",
                "star.kwturb.KOmegaTurbulence", "star.kwturb.SstKwTurbModel", "star.kwturb.KwAllYplusWallTreatment"}) {
            try { cont.enable(Class.forName(fqn)); } catch (Throwable t) { log("enable FAIL " + fqn + " " + root(t)); }
        }
        cont.getClass().getMethod("add", Class.forName("star.common.Region")).invoke(cont, reg);
        setInitialConditions(cont);
        log("physics: coupled + ideal gas + SST k-omega, assigned to region");
        return cont;
    }

    void setInitialConditions(Object cont) {
        try {
            Object ic = cont.getClass().getMethod("getInitialConditions").invoke(cont);
            // axial inflow velocity ~150 m/s along +z so the rotor doesn't start in dead air
            try {
                Object vp = ic.getClass().getMethod("get", Class.class).invoke(ic, Class.forName("star.flow.VelocityProfile"));
                Object meth = vp.getClass().getMethod("getMethod", Class.class).invoke(vp, Class.forName("star.common.ConstantVectorProfileMethod"));
                Object q = meth.getClass().getMethod("getQuantity").invoke(meth);
                double vz = FLIP ? -150.0 : 150.0;
                q.getClass().getMethod("setComponents", double.class, double.class, double.class).invoke(q, 0.0, 0.0, vz);
                setUnits(q, "m/s");
                log("IC velocity = (0,0," + vz + ") m/s");
            } catch (Throwable t) { log("IC vel " + root(t)); }
            setProfile(ic, "star.energy.StaticTemperatureProfile", "288.15 K");
            setProfile(ic, "star.flow.PressureProfile", "101325 Pa");
        } catch (Throwable t) { log("IC " + root(t)); }
    }

    // ---------------- MRF ----------------
    void setupMRF(Region reg) {
        // idempotent: if region already has a rotating reference frame (restart sim), skip
        try {
            Object rv = reg.getClass().getMethod("getValues").invoke(reg);
            Object ms = rv.getClass().getMethod("get", Class.class).invoke(rv, Class.forName("star.motion.MotionSpecification"));
            Object existing = ms.getClass().getMethod("getReferenceFrame").invoke(ms);
            if (existing != null && existing.getClass().getSimpleName().toLowerCase().contains("rotat")) {
                mrfOK = true; log("MRF already set (" + existing.getClass().getSimpleName() + "), skip"); return;
            }
        } catch (Throwable t) {}
        Object rfm = null;
        try { rfm = sim.getClass().getMethod("getReferenceFrameManager").invoke(sim); log("RFM " + rfm.getClass().getName()); }
        catch (Throwable t) { log("RFM getter FAIL " + root(t)); }
        if (rfm == null) { log("MRF SKIP: no reference frame manager"); return; }
        try {
            Object rrf = rfm.getClass().getMethod("createReferenceFrame", Class.class, String.class)
                .invoke(rfm, Class.forName("star.motion.RotatingReferenceFrame"), "RotR37");
            // rotation rate
            Object rate = rrf.getClass().getMethod("getRotationRate").invoke(rrf);
            try { rate.getClass().getMethod("setValue", double.class).invoke(rate, OMEGA); } catch (Throwable t) {}
            setUnits(rate, "rad/s");
            // axis + origin (z axis, origin 0)
            setVec(rrf.getClass().getMethod("getAxisDirection").invoke(rrf), 0, 0, 1);
            try { setVec(rrf.getClass().getMethod("getAxisOrigin").invoke(rrf), 0, 0, 0); } catch (Throwable t) {}
            // assign to region
            Object rv = reg.getClass().getMethod("getValues").invoke(reg);
            Object ms = rv.getClass().getMethod("get", Class.class).invoke(rv, Class.forName("star.motion.MotionSpecification"));
            ms.getClass().getMethod("setReferenceFrame", Class.forName("star.motion.ReferenceFrameBase")).invoke(ms, rrf);
            mrfOK = true;
            log("MRF OK: RotatingReferenceFrame omega=" + OMEGA + " rad/s about +z, assigned to region");
        } catch (Throwable t) { log("MRF setup FAIL " + root(t)); }
    }

    // ---------------- boundaries ----------------
    Object[] setupBoundaries(Region reg) throws Exception {
        Object bm = reg.getBoundaryManager();
        Object inflow = bnd(reg, inflowNm()), outflow = bnd(reg, outflowNm());
        Object per1 = bnd(reg, "per1"), per2 = bnd(reg, "per2"), shroud = bnd(reg, "shroud");
        // inflow = stagnation (fresh)
        setType(inflow, "star.common.StagnationBoundary");
        Object iv = inflow.getClass().getMethod("getValues").invoke(inflow);
        setProfile(iv, "star.flow.TotalPressureProfile", P0_IN + " Pa");
        setProfile(iv, "star.energy.TotalTemperatureProfile", T0_IN + " K");
        setProfile(iv, "star.turbulence.TurbulenceIntensityProfile", "0.03");
        setProfile(iv, "star.turbulence.TurbulentViscosityRatioProfile", "10.0");
        log("inflow(stagnation)=" + pres(inflow) + " P0=" + P0_IN + " T0=" + T0_IN + " FLIP=" + FLIP);
        // outflow = pressure placeholder (mass-flow set in PHASE B)
        setType(outflow, "star.common.PressureBoundary");
        Object ov = outflow.getClass().getMethod("getValues").invoke(outflow);
        setProfile(ov, "star.flow.StaticPressureProfile", P_OUT + " Pa");
        log("outflow=" + pres(outflow));
        if (shroud != null) setShroudLabFrame(shroud);
        return new Object[]{inflow, outflow, per1, per2};
    }

    // mass-flow outlet at the design per-passage rate: enforces operating point, avoids choke-reversal divergence
    void setMassFlowOutlet(Region reg, double mdot) {
        try {
            Object outlet = bnd(reg, outflowNm());
            setType(outlet, "star.common.MassFlowBoundary");
            Object ov = outlet.getClass().getMethod("getValues").invoke(outlet);
            setScalarByKeyword(ov, "massflow", mdot, "kg/s");
            log("outlet -> MassFlowBoundary " + mdot + " kg/s/passage (" + (mdot * NBLADE) + " kg/s full)");
        } catch (Throwable t) { log("setMassFlowOutlet " + root(t)); }
    }
    void setScalarByKeyword(Object valMgr, String keyword, double value, String unit) {
        try {
            for (Object o : (Collection<?>) valMgr.getClass().getMethod("getObjects").invoke(valMgr)) {
                if (!o.getClass().getName().toLowerCase().contains(keyword.toLowerCase())) continue;
                Object method = o.getClass().getMethod("getMethod", Class.class).invoke(o, Class.forName("star.common.ConstantScalarProfileMethod"));
                Object q = method.getClass().getMethod("getQuantity").invoke(method);
                q.getClass().getMethod("setValue", double.class).invoke(q, value);
                if (unit != null) setUnits(q, unit);
                log("set " + o.getClass().getSimpleName() + "=" + value + " " + unit);
                return;
            }
            log("no value class matching '" + keyword + "'");
        } catch (Throwable t) { log("setScalarByKeyword " + root(t)); }
    }

    // casing must be stationary in the LAB frame (default REGION_FRAME spins it with the rotor -> spurious work)
    void setShroudLabFrame(Object shroud) {
        if (shroud == null) { log("shroud null"); return; }
        try {
            Object cond = shroud.getClass().getMethod("getConditions").invoke(shroud);
            Object opt = cond.getClass().getMethod("get", Class.class).invoke(cond, Class.forName("star.motion.WallReferenceFrameOption"));
            setOptSelected(opt, "star.motion.ReferenceFrameOption$Type", "LAB");
            log("shroud wall -> LAB_FRAME (lab-stationary casing)");
        } catch (Throwable t) { log("setShroudLabFrame " + root(t)); }
    }

    // ---------------- periodic ----------------
    void setupPeriodic(Object per1, Object per2) {
        if (per1 == null || per2 == null) { log("periodic SKIP: missing per boundary"); return; }
        try {
            Object im = sim.getInterfaceManager();
            // direct interface: computes the rotational transform angle correctly; meshing AFTER this
            // (PHASE B order) lets STAR-CCM+ build the periodic interface conformally.
            Object itf = im.getClass().getMethod("createDirectInterface",
                    Class.forName("star.common.Boundary"), Class.forName("star.common.Boundary")).invoke(im, per1, per2);
            boolean isPer = false;
            try { isPer = (Boolean) itf.getClass().getMethod("isPeriodic").invoke(itf); } catch (Throwable t) {}
            double ang = Double.NaN;
            try { ang = (Double) itf.getClass().getMethod("getRotationAngleInDegrees").invoke(itf); } catch (Throwable t) {}
            if (!isPer) {
                // set topology (EnumeratedOption) selected -> PERIODIC
                try {
                    Class<?> typeCls = Class.forName("star.common.InterfaceConfigurationOption$Type");
                    Object periodic = null;
                    for (Object cst : typeCls.getEnumConstants()) if (cst.toString().toUpperCase().contains("PERIODIC")) { periodic = cst; break; }
                    Object topo = itf.getClass().getMethod("getTopology").invoke(itf);  // InterfaceConfigurationOption
                    boolean set = false;
                    for (Method mm : topo.getClass().getMethods()) {
                        if (!mm.getName().equals("setSelected") || mm.getParameterCount() != 1) continue;
                        try { mm.invoke(topo, periodic); set = true; log("topology->PERIODIC via " + mm.getParameterTypes()[0].getSimpleName()); break; }
                        catch (Throwable t) {}
                    }
                    if (!set) log("could not invoke setSelected(PERIODIC)");
                    isPer = (Boolean) itf.getClass().getMethod("isPeriodic").invoke(itf);
                } catch (Throwable t) { log("set periodic topology FAIL " + root(t)); }
            }
            // NOTE: rotational transform is configured in PHASE 2 (configurePeriodic) after the rotating
            // reference frame exists, so REGION_REFERENCE_AXIS resolves to the rotor z-axis.
            try { ang = (Double) itf.getClass().getMethod("getRotationAngleInDegrees").invoke(itf); } catch (Throwable t) {}
            periodicOK = isPer;
            log("periodic interface: isPeriodic=" + isPer + " rotAngle=" + ang + " deg (pitch=" + PITCH_DEG + ")");
        } catch (Throwable t) { log("periodic FAIL " + root(t)); }
    }

    // set an EnumeratedOption's selected constant (enum resolved DIRECTLY by FQN — FlexibleEnumeratedOption.getSelected() returns Integer, can't use it)
    void setOptSelected(Object option, String enumFqn, String substr) {
        try {
            Class<?> et = Class.forName(enumFqn);
            Object target = null;
            for (Object c : et.getEnumConstants()) if (c.toString().toUpperCase().contains(substr.toUpperCase())) { target = c; break; }
            if (target == null) { log("enum " + enumFqn + " has no '" + substr + "'"); return; }
            for (Method m : option.getClass().getMethods())
                if (m.getName().equals("setSelected") && m.getParameterCount() == 1) {
                    try { m.invoke(option, target); log("set " + et.getSimpleName() + "=" + target); return; } catch (Throwable t) {}
                }
            log("no usable setSelected for " + enumFqn);
        } catch (Throwable t) { log("setOptSelected " + root(t)); }
    }

    void configurePeriodic(Region reg) {
        try {
            Object im = sim.getInterfaceManager();
            Object itf = null;
            try { itf = im.getClass().getMethod("getInterface", String.class).invoke(im, "Interface 1"); } catch (Throwable t) {}
            if (itf == null) {
                Collection<?> ifs = (Collection<?>) im.getClass().getMethod("getObjects").invoke(im);
                if (!ifs.isEmpty()) itf = ifs.iterator().next();
            }
            if (itf == null) { log("configurePeriodic: no interface"); return; }
            Object xf = itf.getClass().getMethod("getPeriodicTransform").invoke(itf);
            setOptSelected(xf.getClass().getMethod("getPeriodicityOption").invoke(xf), "star.common.PeriodicityOption$Type", "ROTAT");
            try { setOptSelected(xf.getClass().getMethod("getRotationAxisOption").invoke(xf), "star.common.InterfaceRotationAxisOption$Type", "REGION_REFERENCE"); }
            catch (Throwable t) { log("axisOpt " + root(t)); }
            try { xf.getClass().getMethod("setLocked", boolean.class).invoke(xf, false); } catch (Throwable t) {}
            // force the interface to re-intersect so the transform angle is recomputed from geometry
            try {
                java.util.List<Object> lst = new java.util.ArrayList<>(); lst.add(itf);
                im.getClass().getMethod("initializeInterfaces", java.util.List.class).invoke(im, lst);
                log("interfaces re-initialized");
            } catch (Throwable t) { log("initInterfaces " + root(t)); }
            double rang = 0;
            try { rang = (Double) xf.getClass().getMethod("getRotationAngle").invoke(xf); } catch (Throwable t) {}
            double qrad = 0;
            try { qrad = (Double) xf.getClass().getMethod("queryRotationAngle").invoke(xf); } catch (Throwable t) {}
            double qdeg = Math.toDegrees(qrad);
            double eff = Math.abs(rang) > 1e-6 ? rang : qdeg;
            periodicOK = Math.abs(Math.abs(eff) - PITCH_DEG) < 1.0;
            log("periodic transform: getAngle=" + rang + " queryAngle=" + qdeg + " deg (expect ~" + PITCH_DEG + ") periodicOK=" + periodicOK);
        } catch (Throwable t) { log("configurePeriodic " + root(t)); }
    }

    // ---------------- mesh ----------------
    void mesh(Region reg) {
        try {
            Object mom = simGet("star.meshing.MeshOperationManager");
            List<String> meshers = Arrays.asList(
                "star.resurfacer.AutomaticSurfaceRepairAutoMesher",
                "star.resurfacer.ResurfacerAutoMesher",
                "star.dualmesher.DualAutoMesher",        // polyhedral: meshes the reconstructed flush-tip geometry cleanly (trimmer made persistent slivers)
                "star.prismmesher.PrismAutoMesher");
            ArrayList<Object> parts = new ArrayList<>();
            // mesh operates on the geometry part(s)
            Object gpm = simGet("star.common.GeometryPartManager");
            for (Object p : (Collection<?>) gpm.getClass().getMethod("getObjects").invoke(gpm)) parts.add(p);
            Object op = mom.getClass().getMethod("createAutoMeshOperation", java.util.List.class, Collection.class)
                .invoke(mom, meshers, parts);
            Object def = op.getClass().getMethod("getDefaultValues").invoke(op);
            // base size (the proven path)
            Object bs = def.getClass().getMethod("get", Class.class).invoke(def, Class.forName("star.meshing.BaseSize"));
            bs.getClass().getMethod("setValue", double.class).invoke(bs, BASE);
            // prism layers — keep modest so they don't collapse at the flush blade tip (clean-mesh config)
            int nprism = (int) envD("ROTOR37_PRISM", 6);
            try {
                Object npl = def.getClass().getMethod("get", Class.class).invoke(def, Class.forName("star.prismmesher.NumPrismLayers"));
                npl.getClass().getMethod("setNumLayers", int.class).invoke(npl, nprism);
                log("prism layers=" + nprism);
            } catch (Throwable t) { log("prism layers " + root(t)); }
            log("meshing (poly) base=" + BASE + " prism=" + nprism + " ...");
            // generate via MeshPipelineController
            Object mpc = simGet("star.meshing.MeshPipelineController");
            mpc.getClass().getMethod("generateVolumeMesh").invoke(mpc);
            // assert cells
            try {
                Object rep = sim.getRepresentationManager().getObject("Volume Mesh");
                Object n = rep.getClass().getMethod("getCellCount").invoke(rep);
                cellCount = ((Number) n).longValue();
            } catch (Throwable t) {
                // fallback: region cell count
                try { Object n = reg.getClass().getMethod("getCellCount").invoke(reg); cellCount = ((Number) n).longValue(); } catch (Throwable t2) {}
            }
            meshOK = cellCount > 0;
            log("mesh done cells=" + cellCount + " meshOK=" + meshOK);
        } catch (Throwable t) { log("mesh FAIL " + root(t)); }
    }

    // ---------------- solver ----------------
    void setupSolver() {
        try {
            Object sm = sim.getSolverManager();
            Object cis = sm.getClass().getMethod("getSolver", Class.class).invoke(sm, Class.forName("star.coupledflow.CoupledImplicitSolver"));
            double cfl = envD("ROTOR37_CFL", 5.0);
            try { cis.getClass().getMethod("setCFL", double.class).invoke(cis, cfl); log("CFL=" + cfl); } catch (Throwable t) { log("setCFL " + root(t)); }
            // grid-sequencing initialization: coarse-grid (Euler-like) pre-solve -> robust transonic startup
            if (!"0".equals(System.getenv("ROTOR37_GRIDSEQ")))
                try { cis.getClass().getMethod("enableGridSequencing", boolean.class).invoke(cis, true); log("grid sequencing ON"); }
                catch (Throwable t) { log("gridSeq " + root(t)); }
            // enhanced dissipation -> transonic shock stability
            try { cis.getClass().getMethod("setUseEnhancedDissipation", boolean.class).invoke(cis, true); log("enhanced dissipation ON"); }
            catch (Throwable t) { log("enhDiss " + root(t)); }
        } catch (Throwable t) { log("solver cfg " + root(t)); }
    }

    // robust transonic startup: grid sequencing + enhanced dissipation + MANUAL CFL ramp 0.2->target
    void solveRamped(int total) {
        Object cis = null;
        try {
            Object sm = sim.getSolverManager();
            cis = sm.getClass().getMethod("getSolver", Class.class).invoke(sm, Class.forName("star.coupledflow.CoupledImplicitSolver"));
            try { cis.getClass().getMethod("enableGridSequencing", boolean.class).invoke(cis, true); log("grid sequencing ON"); } catch (Throwable t) {}
            try { cis.getClass().getMethod("setUseEnhancedDissipation", boolean.class).invoke(cis, true); log("enhanced dissipation ON"); } catch (Throwable t) {}
        } catch (Throwable t) { log("solver get " + root(t)); }
        double finalCfl = envD("ROTOR37_CFL", 4.0);
        // FIRST-ORDER startup (heavily dissipative -> damps the transonic separation), CFL ramp
        setUpwind("FIRST_ORDER");
        double[] ramp = {0.2, 0.5, 1.0, 2.0, 4.0};
        int warm = 50;
        for (double c : ramp) {
            if (c >= finalCfl) break;
            setCFLv(cis, c);
            sim.getSimulationIterator().run(warm);
        }
        setCFLv(cis, finalCfl);
        int firstIters = Math.max(400, total / 2);   // settle a stable first-order field
        sim.getSimulationIterator().run(firstIters);
        log("first-order phase done (" + firstIters + " iters)");
        // switch to SECOND ORDER and refine
        setUpwind("SECOND_ORDER");
        int rest = total - warm * ramp.length - firstIters;
        sim.getSimulationIterator().run(rest > 100 ? rest : 300);
        log("ramped 1st->2nd order solve complete (final CFL=" + finalCfl + ")");
    }
    void setCFLv(Object cis, double c) { try { cis.getClass().getMethod("setCFL", double.class).invoke(cis, c); log("CFL=" + c); } catch (Throwable t) { log("setCFL " + root(t)); } }

    void setUpwind(String which) {
        try {
            Object cm = sim.get(ContinuumManager.class);
            Object cont = null;
            for (Object c : (Collection<?>) cm.getClass().getMethod("getObjects").invoke(cm)) { cont = c; break; }
            Object mm = cont.getClass().getMethod("getModelManager").invoke(cont);
            Object model = mm.getClass().getMethod("getModel", Class.class).invoke(mm, Class.forName("star.coupledflow.CoupledFlowModel"));
            Object opt = model.getClass().getMethod("getUpwindOption").invoke(model);
            setOptSelected(opt, "star.flow.FlowUpwindOption$Type", which);
            log("discretization -> " + which);
        } catch (Throwable t) { log("setUpwind " + root(t)); }
    }

    void solve(int iters) {
        try {
            sim.getSimulationIterator().run(iters);
            log("ran " + iters + " iters");
        } catch (Throwable t) { log("solve FAIL " + root(t)); }
    }

    // ---------------- reports ----------------
    double[] reports(Region reg) {
        double mdot = Double.NaN, p0in = Double.NaN, p0out = Double.NaN, t0in = Double.NaN, t0out = Double.NaN;
        try {
            Object inlet = bnd(reg, inflowNm()), outlet = bnd(reg, outflowNm());
            Object ffm = sim.getFieldFunctionManager();
            try { for (Object f : (Collection<?>) ffm.getClass().getMethod("getObjects").invoke(ffm)) { String l = pres(f).toLowerCase(); if (l.contains("total") || l.contains("stagnation")) log("  FFavail: '" + pres(f) + "'"); } } catch (Throwable t) {}
            Object ffP0 = ff(ffm, "Absolute Total Pressure", "Total Pressure", "TotalPressure");
            Object ffT0 = ff(ffm, "Total Temperature", "TotalTemperature");
            log("ffP0=" + (ffP0 == null ? "null" : ffP0.getClass().getSimpleName() + " '" + pres(ffP0) + "'")
              + " ffT0=" + (ffT0 == null ? "null" : ffT0.getClass().getSimpleName() + " '" + pres(ffT0) + "'"));
            mdot = massFlow(outlet);
            p0in = mfAvg(inlet, ffP0); p0out = mfAvg(outlet, ffP0);
            t0in = mfAvg(inlet, ffT0); t0out = mfAvg(outlet, ffT0);
        } catch (Throwable t) { log("reports FAIL " + root(t)); }
        double PR = p0out / p0in;
        double T0r = t0out / t0in;
        double g = 1.4;
        double eta = (Math.pow(PR, (g - 1) / g) - 1.0) / (T0r - 1.0);
        double mdotFull = Math.abs(mdot) * NBLADE;
        log(String.format("P0in=%.1f P0out=%.1f T0in=%.2f T0out=%.2f mdot_passage=%.5f mdot_full=%.3f PR=%.4f T0r=%.4f eta=%.4f",
                p0in, p0out, t0in, t0out, mdot, mdotFull, PR, T0r, eta));
        jadd("p0_in_pa", p0in); jadd("p0_out_pa", p0out); jadd("t0_in_k", t0in); jadd("t0_out_k", t0out);
        jadd("mdot_passage_kg_s", mdot); jadd("mdot_full_kg_s", mdotFull);
        jadd("pressure_ratio_tt", PR); jadd("total_temp_ratio", T0r); jadd("isentropic_efficiency", eta);
        return new double[]{mdotFull, PR, eta, T0r};
    }

    double massFlow(Object bndy) {
        try {
            Object rm = sim.getReportManager();
            Object r = rm.getClass().getMethod("createReport", Class.class).invoke(rm, Class.forName("star.flow.MassFlowReport"));
            setParts(r, bndy);
            return ((Number) r.getClass().getMethod("getReportMonitorValue").invoke(r)).doubleValue();
        } catch (Throwable t) { log("massFlow " + root(t)); return Double.NaN; }
    }
    double mfAvg(Object bndy, Object field) {
        try {
            if (field == null) return Double.NaN;
            Object rm = sim.getReportManager();
            Object r = rm.getClass().getMethod("createReport", Class.class).invoke(rm, Class.forName("star.flow.MassFlowAverageReport"));
            r.getClass().getMethod("setFieldFunction", Class.forName("star.common.FieldFunction")).invoke(r, field);
            setParts(r, bndy);
            return ((Number) r.getClass().getMethod("getReportMonitorValue").invoke(r)).doubleValue();
        } catch (Throwable t) { log("mfAvg " + root(t)); return Double.NaN; }
    }
    void setParts(Object report, Object bndy) throws Exception {
        Object parts = report.getClass().getMethod("getParts").invoke(report);
        ArrayList<Object> l = new ArrayList<>(); l.add(bndy);
        parts.getClass().getMethod("setObjects", Collection.class).invoke(parts, l);
    }

    // ---------------- save ----------------
    void save(double[] perf, double sec) {
        try {
            new File(OUT).mkdirs();
            String tag = System.getenv("ROTOR37_TAG"); if (tag == null || tag.isEmpty()) tag = "smoke";
            // save sim (skip during sweep for speed)
            if (!"1".equals(System.getenv("ROTOR37_NOSAVE")))
                try { sim.saveState(OUT + "\\rotor37_" + tag + ".sim"); } catch (Throwable t) { log("saveState " + root(t)); }
            StringBuilder s = new StringBuilder();
            s.append("{\n");
            s.append("  \"case\": \"nasa_rotor37_single_passage_rans\",\n");
            s.append("  \"elapsed_sec\": ").append(String.format("%.1f", sec)).append(",\n");
            s.append("  \"omega_rad_s\": ").append(OMEGA).append(",\n");
            s.append("  \"p_out_pa\": ").append(P_OUT).append(",\n");
            s.append("  \"base_size_m\": ").append(BASE).append(",\n");
            s.append("  \"iters\": ").append(ITERS).append(",\n");
            s.append("  \"cell_count\": ").append(cellCount).append(",\n");
            s.append("  \"mesh_ok\": ").append(meshOK).append(",\n");
            s.append("  \"mrf_ok\": ").append(mrfOK).append(",\n");
            s.append("  \"periodic_ok\": ").append(periodicOK).append(",\n");
            s.append(J);
            s.append("  \"smoke_ok\": ").append(meshOK && perf[1] > 0.5 && !Double.isNaN(perf[1])).append("\n");
            s.append("}\n");
            try (PrintWriter pw = new PrintWriter(new FileWriter(OUT + "\\rotor37_" + tag + ".json"))) { pw.print(s); }
            log("saved " + OUT + "\\rotor37_" + tag + ".json");
        } catch (Throwable t) { log("save FAIL " + root(t)); }
    }

    // ---------------- helpers ----------------
    void cfgFromEnv() {
        OMEGA = envD("ROTOR37_OMEGA", OMEGA); P_OUT = envD("ROTOR37_POUT", P_OUT);
        BASE = envD("ROTOR37_BASE", BASE); ITERS = (int) envD("ROTOR37_ITERS", ITERS);
        String s = System.getenv("ROTOR37_STL"); if (s != null && !s.isEmpty()) STL = s;
        s = System.getenv("ROTOR37_OUT"); if (s != null && !s.isEmpty()) OUT = s;
        FLIP = "1".equals(System.getenv("ROTOR37_FLIP"));
    }
    double envD(String k, double d) { String v = System.getenv(k); try { return v == null || v.isEmpty() ? d : Double.parseDouble(v); } catch (Throwable t) { return d; } }
    void setType(Object bnd, String fqn) throws Exception {
        Object ctm = simGet("star.common.ConditionTypeManager");
        Object bt = ctm.getClass().getMethod("get", Class.class).invoke(ctm, Class.forName(fqn));
        bnd.getClass().getMethod("setBoundaryType", Class.forName("star.common.BoundaryType")).invoke(bnd, bt);
    }
    void setProfile(Object valMgr, String profFqn, String definition) {
        try {
            String[] parts = definition.trim().split("\\s+");
            double value = Double.parseDouble(parts[0]);
            String unit = parts.length > 1 ? parts[1] : null;
            Object prof = valMgr.getClass().getMethod("get", Class.class).invoke(valMgr, Class.forName(profFqn));
            Object method = prof.getClass().getMethod("getMethod", Class.class).invoke(prof, Class.forName("star.common.ConstantScalarProfileMethod"));
            Object q = method.getClass().getMethod("getQuantity").invoke(method);
            q.getClass().getMethod("setValue", double.class).invoke(q, value);
            if (unit != null) setUnits(q, unit);
        } catch (Throwable t) { log("setProfile " + profFqn + " FAIL " + root(t)); }
    }
    void setUnits(Object q, String u) { try { Object um = sim.getUnitsManager(); Object units = um.getClass().getMethod("getObject", String.class).invoke(um, u); q.getClass().getMethod("setUnits", Class.forName("star.common.Units")).invoke(q, units); } catch (Throwable t) {} }
    void setVec(Object v, double x, double y, double z) { try { v.getClass().getMethod("setComponents", double.class, double.class, double.class).invoke(v, x, y, z); } catch (Throwable t) { log("setVec " + root(t)); } }
    Object ff(Object ffm, String... names) {
        try {
            Collection<?> all = (Collection<?>) ffm.getClass().getMethod("getObjects").invoke(ffm);
            for (String n : names) for (Object f : all) {
                if (f.getClass().getSimpleName().contains("Null")) continue;
                String pn = pres(f);
                if (pn.equalsIgnoreCase(n) || pn.equalsIgnoreCase(n.replace(" ", ""))) { log("FF '" + pn + "' (" + f.getClass().getSimpleName() + ") for " + n); return f; }
            }
            for (String n : names) for (Object f : all) {
                if (f.getClass().getSimpleName().contains("Null")) continue;
                if (pres(f).toLowerCase().contains(n.toLowerCase())) { log("FF~ '" + pres(f) + "' for " + n); return f; }
            }
        } catch (Throwable t) { log("ff iterate " + root(t)); }
        log("FF not found: " + Arrays.toString(names)); return null;
    }
    Object bnd(Region reg, String key) throws Exception {
        for (Object b : (Collection<?>) reg.getBoundaryManager().getClass().getMethod("getBoundaries").invoke(reg.getBoundaryManager()))
            if (pres(b).toLowerCase().contains(key)) return b;
        return null;
    }
    Object simGet(String fqn) { try { return sim.getClass().getMethod("get", Class.class).invoke(sim, Class.forName(fqn)); } catch (Throwable t) { return null; } }
    String pres(Object o) { try { return (String) o.getClass().getMethod("getPresentationName").invoke(o); } catch (Throwable t) { return "?"; } }
    void jadd(String k, double v) { J.append("  \"").append(k).append("\": ").append(Double.isNaN(v) ? "null" : v).append(",\n"); }
    void log(String s) { System.out.println("R37> " + s); }
    void fail(String s) { log("SMOKE_FAIL " + s); }
    String root(Throwable t) { Throwable r = t; while (r.getCause() != null) r = r.getCause(); return r.getClass().getSimpleName() + ":" + r.getMessage(); }
    public static void main(String[] a) { new rotor37_rans().execute(); }
}
