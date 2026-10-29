-- BlenderNav: Blender-style numpad navigation for the Roblox Studio viewport (Edit mode).
-- Install: copy this file to %LOCALAPPDATA%\Roblox\Plugins\ and reload plugins (or restart Studio).
--
--   Numpad 1 / Ctrl+1   front / back view        Numpad 4 / 6   orbit left / right (15 deg)
--   Numpad 3 / Ctrl+3   right / left view        Numpad 8 / 2   orbit up / down
--   Numpad 7 / Ctrl+7   top / bottom view        Numpad 9       view from the opposite side
--   Numpad .            frame the selection      Numpad + / -   zoom in / out toward the pivot
--   Home                frame the whole scene    Numpad 5       toggle near-orthographic view
--   Numpad 0            look through the selected part (preview a Markers.Cam_* shot angle)
--
-- The pivot is the centre of the current selection. With nothing selected it keeps the last pivot.
-- Studio's own mouse controls stay as they are: right-drag looks around, middle-drag pans, wheel zooms.
-- Every action is also listed under File > Customize Shortcuts as "BlenderNav: ..." so keys can be rebound.

local RunService = game:GetService("RunService")
if RunService:IsRunning() then
	return -- only drive the editor camera, never a playtest
end

local UserInputService = game:GetService("UserInputService")
local Selection = game:GetService("Selection")

local VERBOSE = true -- prints each action to Output; turn off once the keys feel right
local STEP = math.rad(15)
local ORTHO_FOV = 8

local enabled = true
local lastPivot: Vector3? = nil
local savedFov: number? = nil

local function log(msg: string)
	if VERBOSE then
		print("[BlenderNav] " .. msg)
	end
end

local function camera(): Camera
	return workspace.CurrentCamera
end

-- Centre and radius of a list of instances.
local function boundsOf(list: { Instance }): (Vector3?, number)
	local minV: Vector3?, maxV: Vector3? = nil, nil
	local function add(cf: CFrame, size: Vector3)
		local h = size / 2
		for _, sx in { -1, 1 } do
			for _, sy in { -1, 1 } do
				for _, sz in { -1, 1 } do
					local p = cf * Vector3.new(h.X * sx, h.Y * sy, h.Z * sz)
					minV = if minV then minV:Min(p) else p
					maxV = if maxV then maxV:Max(p) else p
				end
			end
		end
	end
	for _, inst in list do
		if inst:IsA("BasePart") then
			add(inst.CFrame, inst.Size)
		elseif inst:IsA("Model") then
			local ok, cf, size = pcall(inst.GetBoundingBox, inst)
			if ok then
				add(cf, size)
			end
		elseif inst:IsA("Attachment") then
			add(CFrame.new(inst.WorldPosition), Vector3.zero)
		else
			for _, d in inst:GetDescendants() do
				if d:IsA("BasePart") then
					add(d.CFrame, d.Size)
				end
			end
		end
	end
	if not minV or not maxV then
		return nil, 0
	end
	return (minV + maxV) / 2, (maxV - minV).Magnitude / 2
end

local function pivot(): Vector3
	local centre = boundsOf(Selection:Get())
	if centre then
		lastPivot = centre
		return centre
	end
	if lastPivot then
		return lastPivot
	end
	local c = camera().CFrame
	return c.Position + c.LookVector * 30
end

local function place(position: Vector3, target: Vector3, up: Vector3?)
	local cam = camera()
	cam.CFrame = CFrame.lookAt(position, target, up or Vector3.yAxis)
	cam.Focus = CFrame.new(target)
end

local function distanceTo(p: Vector3): number
	local d = (camera().CFrame.Position - p).Magnitude
	return if d < 1 then 30 else d
end

local function orbit(yaw: number, pitch: number)
	local p = pivot()
	local offset = camera().CFrame.Position - p
	local dist = offset.Magnitude
	if dist < 0.1 then
		offset = -camera().CFrame.LookVector * 30
		dist = 30
	end
	local dir = offset.Unit
	local curPitch = math.asin(math.clamp(dir.Y, -1, 1))
	local curYaw = math.atan2(dir.X, dir.Z)
	local newPitch = math.clamp(curPitch + pitch, -math.rad(89), math.rad(89))
	local newYaw = curYaw + yaw
	local newDir = Vector3.new(
		math.cos(newPitch) * math.sin(newYaw),
		math.sin(newPitch),
		math.cos(newPitch) * math.cos(newYaw)
	)
	place(p + newDir * dist, p)
end

-- dir points from the pivot to the camera.
local function view(name: string, dir: Vector3, up: Vector3?)
	local p = pivot()
	place(p + dir * distanceTo(p), p, up)
	log(name .. " view")
end

local function frame(list: { Instance }, label: string)
	local centre, radius = boundsOf(list)
	if not centre then
		log("nothing to frame")
		return
	end
	lastPivot = centre
	local cam = camera()
	local fit = math.max(radius, 2) / math.tan(math.rad(cam.FieldOfView) / 2) * 1.15
	local back = -cam.CFrame.LookVector
	place(centre + back * fit, centre)
	log("framed " .. label)
end

local function zoom(factor: number)
	local p = pivot()
	local offset = camera().CFrame.Position - p
	place(p + offset * factor, p)
end

local function toggleOrtho()
	local cam = camera()
	local p = pivot()
	local offset = cam.CFrame.Position - p
	local fromFov, toFov
	if savedFov then
		fromFov, toFov = ORTHO_FOV, savedFov
		savedFov = nil
	else
		fromFov, toFov = cam.FieldOfView, ORTHO_FOV
		savedFov = cam.FieldOfView
	end
	-- Keep the same framing: move back as the lens narrows.
	local scale = math.tan(math.rad(fromFov) / 2) / math.tan(math.rad(toFov) / 2)
	cam.FieldOfView = toFov
	place(p + offset * scale, p)
	log(if savedFov then "near-orthographic on" else "perspective")
end

local function lookThroughSelection()
	local first = Selection:Get()[1]
	if first and first:IsA("BasePart") then
		camera().CFrame = first.CFrame
		log("looking through " .. first.Name)
	else
		log("select a part (e.g. Markers.Cam_Square_A) to look through it")
	end
end

local function frameAll()
	local list = {}
	for _, child in workspace:GetChildren() do
		if not (child:IsA("Terrain") or child:IsA("Camera") or child.Name == "Baseplate") then
			table.insert(list, child)
		end
	end
	frame(list, "scene")
end

local function flip()
	local p = pivot()
	local offset = camera().CFrame.Position - p
	place(p - offset, p)
	log("opposite view")
end

-- id, label, plain action, ctrl action
local ACTIONS = {
	{ Enum.KeyCode.KeypadOne, "Front view", function() view("front", -Vector3.zAxis) end, function() view("back", Vector3.zAxis) end },
	{ Enum.KeyCode.KeypadThree, "Right view", function() view("right", Vector3.xAxis) end, function() view("left", -Vector3.xAxis) end },
	{ Enum.KeyCode.KeypadSeven, "Top view", function() view("top", Vector3.yAxis, -Vector3.zAxis) end, function() view("bottom", -Vector3.yAxis, Vector3.zAxis) end },
	{ Enum.KeyCode.KeypadNine, "Opposite view", flip },
	{ Enum.KeyCode.KeypadFour, "Orbit left", function() orbit(-STEP, 0) end },
	{ Enum.KeyCode.KeypadSix, "Orbit right", function() orbit(STEP, 0) end },
	{ Enum.KeyCode.KeypadEight, "Orbit up", function() orbit(0, STEP) end },
	{ Enum.KeyCode.KeypadTwo, "Orbit down", function() orbit(0, -STEP) end },
	{ Enum.KeyCode.KeypadPeriod, "Frame selected", function() frame(Selection:Get(), "selection") end },
	{ Enum.KeyCode.Home, "Frame all", frameAll },
	{ Enum.KeyCode.KeypadPlus, "Zoom in", function() zoom(0.8) end },
	{ Enum.KeyCode.KeypadMinus, "Zoom out", function() zoom(1.25) end },
	{ Enum.KeyCode.KeypadFive, "Toggle orthographic", toggleOrtho },
	{ Enum.KeyCode.KeypadZero, "Look through selected part", lookThroughSelection },
}

local byKey = {}
for _, a in ACTIONS do
	byKey[a[1]] = a
	-- Rebindable fallback in File > Customize Shortcuts.
	local ok, action = pcall(function()
		return plugin:CreatePluginAction("BlenderNav_" .. a[1].Name, "BlenderNav: " .. a[2], a[2], "", true)
	end)
	if ok and action then
		action.Triggered:Connect(function()
			if enabled then
				a[3]()
			end
		end)
	end
end

local connection = UserInputService.InputBegan:Connect(function(input)
	if not enabled or input.UserInputType ~= Enum.UserInputType.Keyboard then
		return
	end
	if UserInputService:GetFocusedTextBox() then
		return
	end
	local a = byKey[input.KeyCode]
	if not a then
		return
	end
	local ctrl = UserInputService:IsKeyDown(Enum.KeyCode.LeftControl) or UserInputService:IsKeyDown(Enum.KeyCode.RightControl)
	if ctrl and a[4] then
		a[4]()
	else
		a[3]()
	end
end)

local toolbar = plugin:CreateToolbar("BlenderNav")
local button = toolbar:CreateButton("BlenderNav", "Toggle Blender-style numpad navigation", "")
button.ClickableWhenViewportHidden = true
button:SetActive(enabled)
button.Click:Connect(function()
	enabled = not enabled
	button:SetActive(enabled)
	print("[BlenderNav] " .. (if enabled then "on" else "off"))
end)

plugin.Unloading:Connect(function()
	connection:Disconnect()
end)

print("[BlenderNav] loaded: numpad 1/3/7 views, 4/6/8/2 orbit, . frame, Home frame all, 5 ortho, 0 look through part")
