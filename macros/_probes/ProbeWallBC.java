// ProbeWallBC.java - discover the right method to set wall boundary velocity
// in STAR-CCM+ 19.02.009. Dumps:
//   1) which Condition classes return non-null from bnd.getValues().get()
//   2) all methods on a wall boundary (looking for setVelocity, setTangential,
//      setMotion, etc.)
//   3) whether the wall has a MotionSpecification, VelocitySpecification,
//      or any other wall-specific condition

import star.common.*;
import star.base.neo.*;
import star.meshing.*;
import java.io.*;
import java.util.*;

public class ProbeWallBC extends StarMacro {
    public void execute() {
        Simulation sim = getActiveSimulation();
        sim.println("=== ProbeWallBC START ===");

        // Find the first wall boundary
        RegionManager rm = sim.get(RegionManager.class);
        Collection<?> regions = rm.getRegions();
        if (regions == null || regions.isEmpty()) { sim.println("no regions"); return; }
        Region reg = (Region) regions.iterator().next();
        BoundaryManager bm = reg.getBoundaryManager();
        Collection<?> bds = bm.getBoundaries();
        if (bds == null || bds.isEmpty()) { sim.println("no boundaries"); return; }

        Boundary wall = null;
        for (Object b : bds) {
            Boundary bnd = (Boundary) b;
            String name = bnd.getPresentationName();
            Object bt = bnd.getBoundaryType();
            String btn = (bt == null) ? "null" : bt.getClass().getName();
            if (btn.contains("Wall") || (name != null && (name.toLowerCase().contains("y_max")
                    || name.toLowerCase().contains("x_min")))) {
                wall = bnd;
                sim.println("Using wall: " + name + "  type=" + btn);
                break;
            }
        }
        if (wall == null) { sim.println("no wall found"); return; }

        // Test 1: try a list of condition classes that might be on a wall
        String[] condClasses = {
            "star.boundary.VelocitySpecification",
            "star.boundary.WallBoundaryCondition",
            "star.boundary.WallShearSpecification",
            "star.flow.VelocityProfile",
            "star.flow.VelocityMagnitudeProfile",
            "star.flow.MassFlowRateProfile",
            "star.flow.PressureProfile",
            "star.flow.StaticPressureProfile",
            "star.motion.MotionSpecification",
            "star.motion.TranslationalMotionFrame",
            "star.motion.MotionFrame",
        };
        sim.println("=== Test 1: bnd.getValues().get(<cond>) ===");
        Values values = wall.getValues();
        for (String cls : condClasses) {
            try {
                Class<?> c = Class.forName(cls);
                Object inst = values.get(c);
                if (inst != null) {
                    sim.println("  HAS: " + cls + " -> " + inst.getClass().getName());
                } else {
                    sim.println("  NULL: " + cls);
                }
            } catch (Throwable t) {
                sim.println("  ERR: " + cls + " -> " + t.getClass().getSimpleName() + ": " + t.getMessage());
            }
        }

        // Test 2: enumerate all methods on the wall boundary (with parameter types)
        sim.println("=== Test 2: Wall boundary methods containing 'Velocity' or 'Motion' or 'Tangential' ===");
        try {
            Class<?> bCls = wall.getClass();
            for (java.lang.reflect.Method m : bCls.getMethods()) {
                String n = m.getName();
                if (n.contains("Velocity") || n.contains("Motion") || n.contains("Tangential")) {
                    StringBuilder sb = new StringBuilder("  " + n + "(");
                    Class<?>[] pts = m.getParameterTypes();
                    for (int i = 0; i < pts.length; i++) {
                        if (i > 0) sb.append(",");
                        sb.append(pts[i].getSimpleName());
                    }
                    sb.append(")");
                    sim.println(sb.toString());
                }
            }
        } catch (Throwable t) {
            sim.println("  ERR enumerating methods: " + t);
        }

        // Test 3: try the WallBoundary type class methods too (for motion setting)
        try {
            Object bt = wall.getBoundaryType();
            if (bt != null) {
                sim.println("=== Test 3: WallBoundary TYPE methods containing 'Velocity' or 'Motion' ===");
                for (java.lang.reflect.Method m : bt.getClass().getMethods()) {
                    String n = m.getName();
                    if (n.contains("Velocity") || n.contains("Motion") || n.contains("Tangential")) {
                        StringBuilder sb = new StringBuilder("  " + n + "(");
                        Class<?>[] pts = m.getParameterTypes();
                        for (int i = 0; i < pts.length; i++) {
                            if (i > 0) sb.append(",");
                            sb.append(pts[i].getSimpleName());
                        }
                        sb.append(")");
                        sim.println(sb.toString());
                    }
                }
            }
        } catch (Throwable t) {
            sim.println("  ERR Test 3: " + t);
        }

        sim.println("=== ProbeWallBC END ===");
    }
}
