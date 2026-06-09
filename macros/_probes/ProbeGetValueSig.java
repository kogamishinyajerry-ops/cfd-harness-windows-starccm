// ProbeGetValueSig.java - dump the exact getValue method signatures on a Velocity FF
// We need to know the right Coordinate type and method name.

import star.common.*;
import star.base.neo.*;
import java.lang.reflect.*;

public class ProbeGetValueSig extends StarMacro {
    public void execute() {
        Simulation sim = getActiveSimulation();
        sim.println("=== ProbeGetValueSig START ===");
        try {
            FieldFunctionManager ffm = sim.getFieldFunctionManager();
            sim.println("FFM: " + ffm.getClass().getName());

            // Find Velocity FF
            FieldFunction velFF = null;
            String[] tryNames = {"Velocity", "Vel", "$Velocity"};
            for (String name : tryNames) {
                for (String mName : new String[]{"getFieldFunction", "getFunction", "getByLabel"}) {
                    try {
                        Method m = ffm.getClass().getMethod(mName, String.class);
                        Object o = m.invoke(ffm, name);
                        if (o != null) { velFF = (FieldFunction) o; break; }
                    } catch (Throwable ignore) {}
                }
                if (velFF != null) break;
            }
            if (velFF == null) { sim.println("no Velocity FF"); return; }
            sim.println("velFF: " + velFF.getClass().getName());

            // Enumerate all getValue methods
            sim.println("--- getValue methods on velFF ---");
            for (Method m : velFF.getClass().getMethods()) {
                if (m.getName().equals("getValue")) {
                    StringBuilder sig = new StringBuilder("  getValue(");
                    Class<?>[] pts = m.getParameterTypes();
                    for (int i = 0; i < pts.length; i++) {
                        if (i > 0) sig.append(", ");
                        sig.append(pts[i].getName());
                    }
                    sig.append(") -> ").append(m.getReturnType().getName());
                    sim.println(sig.toString());
                }
            }

            // Try to instantiate some candidate Coordinate classes via getValue()
            sim.println("--- candidate Coordinate classes ---");
            String[] cand = {
                "star.common.Coordinate",
                "star.base.coordinate.CartesianCoordinate",
                "star.base.utility.CartesianCoordinate",
                "star.common.CartesianCoordinate",
                "star.base.utility.Coordinate",
                "star.common.LabCoordinate",
                "star.base.coordinate.Coordinate",
            };
            for (String cn : cand) {
                try {
                    Class<?> c = Class.forName(cn);
                    sim.println("  " + cn + " OK");
                    // list constructors
                    for (Constructor<?> cc : c.getConstructors()) {
                        sim.println("    ctor: " + cc);
                    }
                } catch (Throwable t) {
                    sim.println("  " + cn + " FAIL: " + t.getClass().getSimpleName());
                }
            }

            // Also try: look for any class with "Coordinate" in name
            sim.println("--- (skip exhaustive scan) ---");
            sim.println("=== ProbeGetValueSig END ===");
        } catch (Throwable t) {
            sim.println("FATAL: " + t);
        }
    }
}
