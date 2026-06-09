// ProbeDefEval - try definition.eval(coord) on Ux scalar FF
import star.common.*;
import star.base.neo.*;
import java.lang.reflect.*;

public class ProbeDefEval extends StarMacro {
    public void execute() {
        Simulation sim = getActiveSimulation();
        sim.println("=== ProbeDefEval START ===");
        try {
            FieldFunctionManager ffm = sim.getFieldFunctionManager();
            FieldFunction velFF = ffm.getFunction("Velocity");
            sim.println("velFF class: " + velFF.getClass().getName());
            // Check getDefinition on primitive velFF (not component)
            for (String gn : new String[]{"getDefinition", "getFieldFunctionDefinition", "getFunctionDefinition"}) {
                try {
                    Method gd = velFF.getClass().getMethod(gn);
                    Object def = gd.invoke(velFF);
                    sim.println("velFF." + gn + " OK -> " + def.getClass().getName());
                    if (def != null) {
                        // enumerate eval methods
                        for (Method m : def.getClass().getMethods()) {
                            String n = m.getName();
                            if (n.equals("eval") || n.equals("evaluate") || n.equals("getValue")) {
                                StringBuilder sb = new StringBuilder("  def." + n + "(");
                                Class<?>[] pts = m.getParameterTypes();
                                for (int i = 0; i < pts.length; i++) {
                                    if (i > 0) sb.append(", ");
                                    sb.append(pts[i].getName());
                                }
                                sb.append(") -> ").append(m.getReturnType().getName());
                                sim.println(sb.toString());
                            }
                        }
                    }
                } catch (NoSuchMethodException nsme) { sim.println("velFF." + gn + " NOT FOUND"); }
                catch (Throwable t) { sim.println("velFF." + gn + " err: " + t); }
            }
            // also check the magnitude FF
            FieldFunction magFF = velFF.getMagnitudeFunction();
            sim.println("magFF class: " + magFF.getClass().getName());
            for (String gn : new String[]{"getDefinition", "getFieldFunctionDefinition"}) {
                try {
                    Method gd = magFF.getClass().getMethod(gn);
                    Object def = gd.invoke(magFF);
                    sim.println("magFF." + gn + " OK -> " + def.getClass().getName());
                } catch (Throwable t) { sim.println("magFF." + gn + " err: " + t); }
            }
            FieldFunction uxFF = velFF.getComponentFunction(0);
            sim.println("uxFF class: " + uxFF.getClass().getName());

            // Try getDefinition
            Object def = null;
            Method defEval = null;
            for (String gn : new String[]{"getDefinition", "getFieldFunctionDefinition",
                                           "getFunctionDefinition"}) {
                try {
                    Method gd = uxFF.getClass().getMethod(gn);
                    def = gd.invoke(uxFF);
                    if (def != null) {
                        sim.println("getDefinition via " + gn + " OK -> " + def.getClass().getName());
                        break;
                    }
                } catch (NoSuchMethodException nsme) { /* try next */ }
                catch (Throwable t) { sim.println("  " + gn + " err: " + t); }
            }
            if (def == null) {
                sim.println("no getDefinition method found; trying parent classes");
                for (Class<?> c = uxFF.getClass().getSuperclass(); c != null; c = c.getSuperclass()) {
                    sim.println("  superclass: " + c.getName());
                    for (String gn : new String[]{"getDefinition", "getFieldFunctionDefinition"}) {
                        try {
                            Method gd = c.getMethod(gn);
                            def = gd.invoke(uxFF);
                            if (def != null) {
                                sim.println("  found via super " + c.getSimpleName() + "." + gn);
                                break;
                            }
                        } catch (Throwable t) {}
                    }
                    if (def != null) break;
                }
            }
            if (def == null) {
                sim.println("no definition found at all");
                return;
            }
            // Enumerate definition methods
            sim.println("--- definition methods ---");
            for (Method m : def.getClass().getMethods()) {
                String n = m.getName();
                if (n.equals("eval") || n.equals("evaluate") || n.equals("getValue")
                        || n.equals("sample") || n.contains("Definition")) {
                    StringBuilder sb = new StringBuilder("  " + n + "(");
                    Class<?>[] pts = m.getParameterTypes();
                    for (int i = 0; i < pts.length; i++) {
                        if (i > 0) sb.append(", ");
                        sb.append(pts[i].getName());
                    }
                    sb.append(") -> ").append(m.getReturnType().getName());
                    sim.println(sb.toString());
                }
            }
            // Try eval(coord) with various coord types
            for (String cn : new String[]{
                    "star.common.Coordinate", "star.base.coordinate.CartesianCoordinate",
                    "star.base.utility.CartesianCoordinate", "star.base.neo.DoubleVector"}) {
                Method evalM = null;
                Class<?> coordCls = null;
                try {
                    coordCls = Class.forName(cn);
                    // find eval method taking this coord type
                    for (Method m : def.getClass().getMethods()) {
                        if ((m.getName().equals("eval") || m.getName().equals("evaluate"))
                                && m.getParameterTypes().length == 1
                                && m.getParameterTypes()[0] == coordCls) {
                            evalM = m; break;
                        }
                    }
                    if (evalM == null) {
                        sim.println("  no eval(" + cn + ")");
                        continue;
                    }
                    // build coord
                    Object coord = null;
                    if (cn.equals("star.base.neo.DoubleVector")) {
                        coord = coordCls.getConstructor(double[].class).newInstance(new double[]{0.5, 0.5, 0.005});
                    } else if (cn.equals("star.common.Coordinate")) {
                        // Use setComponents via ClientServerObjectKey
                        coord = coordCls.getConstructor(Class.forName("star.base.neo.ClientServerObjectKey"))
                            .newInstance((Object) null);
                        coordCls.getMethod("setComponents", double.class, double.class, double.class)
                            .invoke(coord, 0.5, 0.5, 0.005);
                    } else {
                        // CartesianCoordinate
                        coord = coordCls.getConstructor(double[].class).newInstance(new double[]{0.5, 0.5, 0.005});
                    }
                    Object val = evalM.invoke(def, coord);
                    sim.println("  eval(" + cn + ") -> " + val + "  (class=" + val.getClass().getName() + ")");
                    if (val instanceof Number) {
                        sim.println("    SUCCESS: Ux(0.5, 0.5, 0.005) = " + ((Number) val).doubleValue());
                    }
                } catch (Throwable t) {
                    sim.println("  eval(" + cn + ") FAIL: " + t.getClass().getSimpleName() + ": " + t.getMessage());
                }
            }
        } catch (Throwable t) {
            sim.println("FATAL: " + t);
        }
        sim.println("=== ProbeDefEval END ===");
    }
}