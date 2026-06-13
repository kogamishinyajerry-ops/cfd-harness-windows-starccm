// Probe17.java — FINAL probe
// Last-ditch: try sff.getValue(coordinate) for the SCALAR uxFF
// (not the vector Velocity). The probes all tried velFF.getValue() and
// got no-args; but uxFF is a different class. The 8 previous probes
// tried uxFF.getValue but only with the same no-args signature; they
// never tried getValue(Coordinate) on uxFF specifically.
//
// Also: try InternalFieldFunction or FieldFunctionWrapper
import star.common.*;
import star.base.neo.*;
import java.io.*;
import java.lang.reflect.*;
import java.util.*;

public class Probe17 extends StarMacro {
    public void execute() {
        Simulation sim = getActiveSimulation();
        sim.println("=== Probe17 START ===");
        PrintWriter pw = null;
        try {
            pw = new PrintWriter(new FileWriter(
                "D:\\CFD-harness-Windows-StarCCM\\probe17_scalar_getvalue.log"));
        } catch (Throwable t) { sim.println("can't open log: " + t); return; }
        try {
            FieldFunctionManager ffm = sim.getFieldFunctionManager();
            FieldFunction velFF = ffm.getFunction("Velocity");
            FieldFunction uxFF = velFF.getComponentFunction(0);

            // Enumerate ALL methods on uxFF (VectorComponentFieldFunction)
            pw.println("=== ALL uxFF methods (no filter) ===");
            int cnt = 0;
            for (Method m : uxFF.getClass().getMethods()) {
                StringBuilder sb = new StringBuilder();
                sb.append("  ");
                sb.append(m.getName()).append("(");
                Class<?>[] pts = m.getParameterTypes();
                for (int i = 0; i < pts.length; i++) {
                    if (i > 0) sb.append(", ");
                    sb.append(pts[i].getName());
                }
                sb.append(") -> ").append(m.getReturnType().getName());
                if (sb.length() < 200) { pw.println(sb.toString()); cnt++; }
            }
            pw.println("(" + cnt + " methods)");

            // Try getValue with any 1-arg signature
            pw.println("=== getValue(ANY) attempts on uxFF ===");
            for (Method m : uxFF.getClass().getMethods()) {
                if (m.getName().equals("getValue") && m.getParameterTypes().length == 1) {
                    Class<?> argType = m.getParameterTypes()[0];
                    StringBuilder sb = new StringBuilder();
                    sb.append("  uxFF.getValue(").append(argType.getSimpleName()).append(") -> ").append(m.getReturnType().getSimpleName());
                    pw.println(sb.toString());
                    // Try with a null arg
                    try {
                        Object r = m.invoke(uxFF, (Object) null);
                        pw.println("    getValue(null) = " + r);
                    } catch (Throwable t) { pw.println("    getValue(null) FAIL: " + t.getMessage()); }
                    // Try building a coord instance via reflection
                    // First find any Coordinate class
                    String[] coordClassNames = {
                        "star.common.Coordinate", "star.base.neo.Coordinate",
                        "star.common.SolidCoordinate", "star.common.DoubleVector",
                        "java.awt.geom.Point2D", "java.awt.geom.Point2D.Double"
                    };
                    for (String cn : coordClassNames) {
                        try {
                            Class<?> cc = Class.forName(cn);
                            Object c = null;
                            // try to build one
                            try {
                                if (cc.getConstructors().length > 0) {
                                    for (Constructor<?> ctor : cc.getConstructors()) {
                                        if (ctor.getParameterCount() == 3 && ctor.getParameterTypes()[0] == double.class) {
                                            c = ctor.newInstance(0.5, 0.5, 0.005);
                                            break;
                                        }
                                        if (ctor.getParameterCount() == 1 && ctor.getParameterTypes()[0] == double.class) {
                                            // DoubleVector: try fill later
                                        }
                                    }
                                }
                            } catch (Throwable ignored) {}
                            if (c != null && argType.isInstance(c)) {
                                try {
                                    Object r = m.invoke(uxFF, c);
                                    pw.println("    getValue(" + cn + ") = " + r);
                                } catch (Throwable t) { pw.println("    getValue(" + cn + ") FAIL: " + t.getMessage()); }
                            }
                        } catch (ClassNotFoundException cnf) { /* skip */ }
                    }
                }
            }

            // Try uxFF's parent class for getValue
            pw.println("=== uxFF superclass chain getValue ===");
            for (Class<?> c = uxFF.getClass().getSuperclass(); c != null && c != Object.class; c = c.getSuperclass()) {
                pw.println("  super: " + c.getName());
                for (Method m : c.getDeclaredMethods()) {
                    if (m.getName().equals("getValue")) {
                        StringBuilder sb = new StringBuilder("    ");
                        sb.append("getValue(");
                        Class<?>[] pts = m.getParameterTypes();
                        for (int i = 0; i < pts.length; i++) {
                            if (i > 0) sb.append(", ");
                            sb.append(pts[i].getSimpleName());
                        }
                        sb.append(") -> ").append(m.getReturnType().getSimpleName());
                        pw.println(sb.toString());
                    }
                }
            }

        } catch (Throwable t) {
            pw.println("FATAL: " + t);
        }
        pw.close();
        sim.println("=== Probe17 END ===");
    }
}
