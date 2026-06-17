// render_scenes.java — Rotor 37 RANS 后处理云图渲染 (surface scalar scenes).
// Loads a solved .sim ONCE, renders multiple field-function surface contours from
// well-framed camera angles, exports PNGs to figs/.
// NOTE: the loaded field is the FIRST-ORDER converged *non-physical surge* solution;
// these images demonstrate the post-processing / rendering pipeline and the real
// reconstructed geometry+mesh, NOT a validated compressor flow.  (See REPORT.)
//
// Run:  starccm+.bat <solved.sim> -batch render_scenes.java -np 4
import star.common.*;
import star.base.neo.*;
import star.vis.*;
import java.util.*;

public class render_scenes extends StarMacro {
    static final String OUT = "D:/CFD-harness-Windows-StarCCM/reproductions/rotor37_rans/figs/";
    static final int W = 1600, H = 1000;

    public void execute() {
        Simulation sim = getActiveSimulation();
        sim.println("[render] start; regions/cells:");
        try {
            for (Object r : sim.getRegionManager().getRegions())
                sim.println("  region " + ((Region) r).getPresentationName());
        } catch (Exception e) {}

        // Explicit camera placement. Passage bbox: x[-.03,.03] y[.17,.255] z[-.049,.153]
        // focal = bbox centre; camera placed along a view normal at distance d.
        // sector sits at theta~90deg (+y), z = machine axis.
        // broadside blade-to-blade: look along -y; image plane = x(pitch) vs z(axial)
        double[] bbPos = {0.0, 0.6325, 0.052};  double[] bbUp = {0.0, 0.0, 1.0};
        // oblique 3D
        double[] obPos = {0.236, 0.6065, 0.249}; double[] obUp = {0.0, 0.0, 1.0};
        // meridional side: look along -x; r(=y) vertical vs z(axial) horizontal
        double[] mrPos = {0.42, 0.2125, 0.052}; double[] mrUp = {0.0, 1.0, 0.0};

        // field -> {prettyTag, lutName}
        String[][] fields = {
            {"Absolute Total Pressure", "ptot",  "thermal"},
            {"Mach Number",             "mach",  "spectrum"},
            {"Velocity: Magnitude",     "vmag",  "spectrum"},
            {"Temperature",             "temp",  "thermal"},
            {"Pressure",                "pstat", "blue-red"},
        };

        for (String[] f : fields) {
            renderField(sim, f[0], f[1] + "_bb",  f[2], bbPos, bbUp);
        }
        // extra angles for the headline fields
        renderField(sim, "Absolute Total Pressure", "ptot_ob", "thermal",  obPos, obUp);
        renderField(sim, "Mach Number",             "mach_mr", "spectrum", mrPos, mrUp);
        renderField(sim, "Temperature",             "temp_mr", "thermal",  mrPos, mrUp);

        sim.println("[render] ALL DONE");
    }

    static final double[] FOCAL = {0.0, 0.2125, 0.052};

    void renderField(Simulation sim, String fieldName, String tag, String lut,
                     double[] pos, double[] up) {
        try {
            FieldFunction ff = resolveFF(sim, fieldName);
            if (ff == null) { sim.println("[render] SKIP (no FF): " + fieldName); return; }

            Scene scene = sim.getSceneManager().createScene("S_" + tag);
            scene.initializeAndWait();
            ScalarDisplayer sd = scene.getDisplayerManager()
                .createScalarDisplayer("disp_" + tag, star.vis.ClipMode.NONE);
            sd.getScalarDisplayQuantity().setFieldFunction(ff);
            // Temperature has a spurious hot outlier cell (~5500K) in the surge
            // field that blows the auto scale; clamp to the physical band so the
            // inlet recirculation heating (the surge signature) is legible.
            if (fieldName.equalsIgnoreCase("Temperature")) {
                sd.getScalarDisplayQuantity().setRangeMin(250.0);
                sd.getScalarDisplayQuantity().setRangeMax(460.0);
            } else {
                sd.getScalarDisplayQuantity().setAutoRange(AutoRangeMode.BOTH);
            }

            // attach every external boundary of every region
            int added = 0;
            for (Object rObj : sim.getRegionManager().getRegions()) {
                Region reg = (Region) rObj;
                for (Object b : reg.getBoundaryManager().getBoundaries()) {
                    Boundary bnd = (Boundary) b;
                    if (!(bnd.getBoundaryType() instanceof star.common.InternalBoundary)) {
                        try { sd.addPart((NamedObject) bnd); added++; } catch (Exception ae) {}
                    }
                }
            }
            sim.println("[render] " + tag + ": FF=" + ff.getPresentationName() + " parts=" + added);

            // legend
            try {
                Legend lg = sd.getLegend();
                lg.setLevels(32); lg.setNumberOfLabels(4);
                lg.setLabelFormat("%.3g");
                try {
                    LookupTableManager ltm = sim.getLookupTableManager();
                    Object lto = ltm.getObject(lut);
                    if (lto instanceof LookupTable) lg.setLookupTable((LookupTable) lto);
                } catch (Exception le) {}
            } catch (Exception lge) {}

            // camera — deterministic explicit placement (setViewOrientation is a
            // no-op in batch). Perspective; no resetCamera (would refit & override).
            try {
                CoordinateSystem lab = sim.getCoordinateSystemManager().getLabCoordinateSystem();
                scene.getCurrentView().setInput(
                    new DoubleVector(FOCAL), new DoubleVector(pos), new DoubleVector(up),
                    0.12, 0, lab, false);
            } catch (Exception ve) { sim.println("[render] view FAIL: " + ve.getMessage()); }
            try { Thread.sleep(3500); } catch (Exception e) {}

            java.io.File out = new java.io.File(OUT + "cfd_" + tag + ".png");
            try {
                scene.printAndWait(out, 1, W, H);
            } catch (Exception pe) {
                sim.println("[render] 4-arg print fail, try 1-arg: " + pe.getMessage());
                scene.printAndWait(out);
            }
            sim.println("[render] saved " + out.getName() + " exists=" + out.exists()
                + " bytes=" + (out.exists() ? out.length() : -1));
        } catch (Exception e) {
            sim.println("[render] FAIL " + tag + ": " + e);
        }
    }

    // Resolve a field function robustly (handles Velocity:Magnitude derived FF)
    FieldFunction resolveFF(Simulation sim, String fieldName) {
        FieldFunctionManager ffm = sim.getFieldFunctionManager();
        try {
            if (fieldName.toLowerCase().contains("magnitude")
                && fieldName.toLowerCase().contains("vel")) {
                FieldFunction vec = ffm.getFunction("Velocity");
                if (isReal(vec)) {
                    java.lang.reflect.Method m = ffm.getClass()
                        .getMethod("getVectorMagnitudeFunction", FieldFunction.class);
                    Object mag = m.invoke(ffm, vec);
                    if (mag instanceof FieldFunction) return (FieldFunction) mag;
                }
            }
        } catch (Exception e) {}
        String[] aliases = { fieldName, fieldName.replace(":", ""), fieldName.replace(": ", " "),
                             fieldName.replace(" ", "") };
        for (String a : aliases) {
            try { FieldFunction p = ffm.getFunction(a); if (isReal(p)) return p; } catch (Exception e) {}
        }
        try {
            String want = fieldName.toLowerCase().replaceAll("[ :._-]", "");
            java.lang.reflect.Method m = ffm.getClass().getMethod("getObjects");
            Object col = m.invoke(ffm);
            if (col instanceof java.util.Collection) {
                for (Object o : (java.util.Collection<?>) col) {
                    FieldFunction fc = (FieldFunction) o;
                    if (!isReal(fc)) continue;
                    String nl = fc.getPresentationName().toLowerCase().replaceAll("[ :._-]", "");
                    if (nl.equals(want) || nl.contains(want)) return fc;
                }
            }
        } catch (Exception e) {}
        return null;
    }

    boolean isReal(FieldFunction ff) {
        if (ff == null) return false;
        String n = ff.getPresentationName();
        return n != null && !n.startsWith("<") && !n.isEmpty();
    }
}
