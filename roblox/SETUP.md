# StoryKit setup: Roblox Studio + Claude

## 1. Install Roblox Studio
Your PC has the Roblox player but not Studio. Download it from https://create.roblox.com (click **Start Creating**), sign in, and open a new **Baseplate** place. Save it as `EverydayMyths.rbxl`.

## 2. Turn on Studio's MCP server
1. Open the **Assistant** panel.
2. Click **… → Manage MCP Servers**.
3. Turn on **Enable Studio as MCP server**.

## 3. Connect Claude Code
**Quick connect (easiest):** in the same panel, open **Quick connect** and turn on **Claude Code**.
If Claude Code isn't listed, restart Studio once.

**Manual alternative:** add this to a `.mcp.json` file in your project folder:

```json
{
  "mcpServers": {
    "Roblox_Studio": {
      "command": "cmd.exe",
      "args": ["/c", "%LOCALAPPDATA%\\Roblox\\mcp.bat"]
    }
  }
}
```

Then **start a new Claude Code session**. MCP servers load when a session starts, so the session where they were added won't see them. With Studio open, the panel shows a green indicator and a count of connected clients. Claude will then have tools such as `execute_luau`, `multi_edit`, `start_stop_play` and `screen_capture`.

Only connect clients you trust: a connected client can read and change your open place.

## 4. Install StoryKit
Do this by hand, or once the connection works, ask Claude to do it with `multi_edit`.

| File | Where in Studio | Type |
|---|---|---|
| `StoryKit/CameraRig.luau` | ReplicatedStorage › Folder `StoryKit` › `CameraRig` | ModuleScript |
| `StoryKit/LightingPresets.luau` | ReplicatedStorage › `StoryKit` › `LightingPresets` | ModuleScript |
| `StoryKit/NumberBillboard.luau` | ReplicatedStorage › `StoryKit` › `NumberBillboard` | ModuleScript |
| `EP01_Shots.client.luau` | StarterPlayer › StarterPlayerScripts › `EP01_Shots` | LocalScript |

The names must match exactly. Paste each file's contents into its script.

## 5. Test
1. Use **Avatar tab → Rig Builder** to add a rig, rename it `Hero`, and turn it to face open space.
2. Press **Play**. The camera frames the Hero at dawn with "212" above its head.
3. Press **1** for shot 01 (push-in while the number glows in), **2** for the montage (900 → 3,000 → 10,000, day fading to dusk), and **0** to reset.
4. To record, resize the Studio window to 9:16 and capture it with OBS at 1080×1920, 60 fps.

## Using the helpers in your own shots

```lua
CameraRig.take()
Light.apply("pre_dawn_dark")
local baker = NumberBillboard.attach(workspace.Baker, { value = 9 })
CameraRig.play({ kind = "pan", duration = 3, shake = 0.1,
    from = { pos = "Markers.Cam_Street_A", look = "Door_1" },
    to   = { pos = "Markers.Cam_Street_B", look = "Door_2" } })
baker:dim(0.6, 1)   -- shot 14: the baker is sick
```

- **Camera moves:** `static`, `push_in`, `pull_out`, `pan`, `crane` (all from → to), `orbit` (center, radius, startAngle → endAngle), plus `cut()` and `snapZoom()`.
- **Lighting presets:** `pre_dawn_dark`, `dawn`, `day`, `dusk`, `night`. Tune the numbers in `PRESETS` once against your map, then keep them fixed across episodes.

## Recording an episode with OBS (vertical 1080×1920)
1. **Studio:** on the **Test** tab, open **Device** and pick a phone in portrait. Close the side panels (Explorer, Properties, Toolbox) so the game view is as big as possible.
2. **OBS → Settings → Video:** Base and Output resolution **1080×1920**, FPS **60**.
3. **OBS → Settings → Output → Recording:** format **mp4**, encoder **NVENC** (NVIDIA) or x264, quality **High** or better.
4. **Source:** add **Window Capture** → the Studio window. Right-click → **Transform → Edit Transform**, crop to the game view, then **Fit to screen**.
5. **Audio:** mute OBS audio sources; voice and music are added in the edit.
6. **Record:** press Play in Studio, click in the game view, **Start Recording** in OBS, press **P**. Stop after the final crane.
