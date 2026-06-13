import star.common.*;
import star.base.neo.*;
// skip typed scene import
import java.io.*;
import java.lang.reflect.*;
import java.util.*;

public class ExportScene extends StarMacro {
    public void execute() {
        Simulation sim = getActiveSimulation();
        try {
            // Get scene manager
            Object sm = sim.getClass().getMethod("getSceneManager").invoke(sim);
            // List scenes
            Method getScenes = sm.getClass().getMethod("getScenes");
            java.util.List scenes = (java.util.List) getScenes.invoke(sm);
            System.out.println("Scenes: " + scenes.size());
            for (Object s : scenes) {
                String n = (String) s.getClass().getMethod("getPresentationName").invoke(s);
                System.out.println("  scene: " + n);
            }
            // Create a new scene showing the parts
            Method createScene = sm.getClass().getMethod("createScene");
            Object scene = createScene.invoke(sm);
            scene.getClass().getMethod("setPresentationName", String.class).invoke(scene, "R37_Scene");
            // Add the parts
            // ... skip
            // Hard: need to wire up scalar/vector display. Skip for now.
            // Activate and save snapshot
            // (star.scene.Scene.Activate + hard)
            System.out.println("Scene created: " + scene);
        } catch (Throwable t) {
            System.out.println("scene FAIL: " + t);
            t.printStackTrace();
        }
    }
}
