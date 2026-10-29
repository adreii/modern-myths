-- BuildEP01Extras
-- Adds what the 18 EP01 shots need on top of BuildEP01Map: the crowd and the kid, the props
-- (bread, basket, bread bag, phone), the Baker's bedroom set for shot 14, and the floating
-- numbers over the town for shot 18. Run in Edit mode after BuildEP01Map. Safe to re-run.

local Players = game:GetService("Players")

for _, name in { "Crowd", "Props", "SkyNumbers" } do
	local old = workspace:FindFirstChild(name)
	if old then
		old:Destroy()
	end
end
local oldRoom = workspace.EP01_Map:FindFirstChild("BakerBedroom")
if oldRoom then
	oldRoom:Destroy()
end

local function part(parent: Instance, name: string, size: Vector3, cf: CFrame, color: Color3, material: Enum.Material?): Part
	local p = Instance.new("Part")
	p.Name = name
	p.Anchored = true
	p.Size = size
	p.CFrame = cf
	p.Color = color
	p.Material = material or Enum.Material.SmoothPlastic
	p.TopSurface = Enum.SurfaceType.Smooth
	p.BottomSurface = Enum.SurfaceType.Smooth
	p.Parent = parent
	return p
end

-- Rigs: strip any default Animate script so nothing fights the Puppet module.
local function stripAnimate(model: Model)
	for _, d in model:GetDescendants() do
		if d.Name == "Animate" and (d:IsA("Script") or d:IsA("LocalScript")) then
			d:Destroy()
		end
	end
end
for _, name in { "Hero", "Baker", "Influencer" } do
	local m = workspace:FindFirstChild(name)
	if m then
		stripAnimate(m)
	end
end

local function rig(name: string, parent: Instance, torso: Color3, legs: Color3, skin: Color3, scale: number?): Model?
	local desc = Instance.new("HumanoidDescription")
	desc.HeadColor = skin
	desc.LeftArmColor = skin
	desc.RightArmColor = skin
	desc.TorsoColor = torso
	desc.LeftLegColor = legs
	desc.RightLegColor = legs
	local ok, m = pcall(function()
		return Players:CreateHumanoidModelFromDescription(desc, Enum.HumanoidRigType.R15)
	end)
	if not ok or not m then
		warn(`BuildEP01Extras: couldn't create {name}: {m}`)
		return nil
	end
	m.Name = name
	stripAnimate(m)
	if scale then
		m:ScaleTo(scale)
	end
	local root = m:FindFirstChild("HumanoidRootPart") :: BasePart?
	if root then
		root.Anchored = true
	end
	m:PivotTo(CFrame.new(0, 3, 0))
	m.Parent = parent
	return m
end

-- Crowd (the shot script places them each shot)
local crowd = Instance.new("Folder")
crowd.Name = "Crowd"
crowd.Parent = workspace
local skins = { Color3.fromRGB(234, 190, 150), Color3.fromRGB(198, 140, 100), Color3.fromRGB(140, 95, 65), Color3.fromRGB(250, 215, 180) }
local shirts = {
	Color3.fromRGB(230, 90, 70), Color3.fromRGB(80, 160, 110), Color3.fromRGB(240, 190, 60), Color3.fromRGB(120, 110, 200),
	Color3.fromRGB(60, 150, 200), Color3.fromRGB(200, 120, 170), Color3.fromRGB(150, 150, 150),
}
for i = 1, 7 do
	rig(`Crowd_{i}`, crowd, shirts[i], Color3.fromRGB(50 + i * 8, 50, 60), skins[(i % #skins) + 1])
end
rig("Kid", crowd, Color3.fromRGB(255, 160, 60), Color3.fromRGB(60, 80, 140), skins[1], 0.7)

-- Props (hidden below the map until a shot uses them)
local props = Instance.new("Folder")
props.Name = "Props"
props.Parent = workspace
local bread = Color3.fromRGB(196, 140, 80)
for i, x in { -45, -15, 15, 45 } do
	local loaf = part(props, `Bread_{i}`, Vector3.new(2.6, 1.3, 1.4), CFrame.new(x + 1.6, 1.45, -70.6), bread, Enum.Material.Sand)
	loaf.Shape = Enum.PartType.Cylinder
	loaf.Transparency = 1
	loaf.CanCollide = false
end
part(props, "Basket", Vector3.new(1.8, 1, 1.3), CFrame.new(0, -60, 0), Color3.fromRGB(150, 105, 60), Enum.Material.WoodPlanks).CanCollide = false
part(props, "BreadBag", Vector3.new(1.2, 1.6, 0.8), CFrame.new(0, -60, 2), Color3.fromRGB(215, 185, 140), Enum.Material.Fabric).CanCollide = false
part(props, "Phone", Vector3.new(0.2, 1, 0.55), CFrame.new(0, -60, 4), Color3.fromRGB(20, 20, 25), Enum.Material.Glass).CanCollide = false

-- Baker's bedroom: an open set far east of town, seen through its front window (shot 14).
local room = Instance.new("Model")
room.Name = "BakerBedroom"
room.Parent = workspace.EP01_Map
local wall = Color3.fromRGB(205, 160, 200)
local inside = Color3.fromRGB(235, 225, 210)
local cx, cz = 150, -84
part(room, "Floor", Vector3.new(20, 1, 16), CFrame.new(cx, 0.05, cz), Color3.fromRGB(150, 110, 75), Enum.Material.WoodPlanks)
part(room, "BackWall", Vector3.new(20, 14, 1), CFrame.new(cx, 7, cz - 7.5), inside)
part(room, "LeftWall", Vector3.new(1, 14, 16), CFrame.new(cx - 9.5, 7, cz), inside)
part(room, "RightWall", Vector3.new(1, 14, 16), CFrame.new(cx + 9.5, 7, cz), inside)
part(room, "Ceiling", Vector3.new(20, 1, 16), CFrame.new(cx, 14.5, cz), inside)
-- Front wall with a 7 x 5 window opening (x 146.5..153.5, y 4..9)
local fz = cz + 7.5
part(room, "FrontLeft", Vector3.new(6.5, 14, 1), CFrame.new(cx - 6.75, 7, fz), wall, Enum.Material.Brick)
part(room, "FrontRight", Vector3.new(6.5, 14, 1), CFrame.new(cx + 6.75, 7, fz), wall, Enum.Material.Brick)
part(room, "FrontBelow", Vector3.new(7, 4, 1), CFrame.new(cx, 2, fz), wall, Enum.Material.Brick)
part(room, "FrontAbove", Vector3.new(7, 5, 1), CFrame.new(cx, 11.5, fz), wall, Enum.Material.Brick)
part(room, "WindowSill", Vector3.new(7.6, 0.4, 1.6), CFrame.new(cx, 4.1, fz + 0.2), Color3.fromRGB(240, 240, 240))
part(room, "BedFrame", Vector3.new(7, 1.4, 4), CFrame.new(cx, 1.2, cz - 2.5), Color3.fromRGB(120, 85, 60), Enum.Material.Wood)
part(room, "Mattress", Vector3.new(6.6, 0.6, 3.6), CFrame.new(cx, 2.2, cz - 2.5), Color3.fromRGB(245, 245, 250), Enum.Material.Fabric)
part(room, "Pillow", Vector3.new(1.4, 0.5, 2.6), CFrame.new(cx - 2.5, 2.7, cz - 2.5), Color3.fromRGB(255, 255, 255), Enum.Material.Fabric)
part(room, "Blanket", Vector3.new(3.6, 0.3, 3.7), CFrame.new(cx + 1.2, 3.1, cz - 2.5), Color3.fromRGB(110, 140, 200), Enum.Material.Fabric)
local lamp = part(room, "Lamp", Vector3.new(0.8, 0.8, 0.8), CFrame.new(cx + 5, 3, cz - 5), Color3.fromRGB(255, 220, 150), Enum.Material.Neon)
local glow = Instance.new("PointLight")
glow.Color = Color3.fromRGB(255, 200, 140)
glow.Range = 14
glow.Brightness = 1.2
glow.Parent = lamp

local cam = workspace.Markers:FindFirstChild("Cam_BakerWindow")
if cam then
	cam.CFrame = CFrame.lookAt(Vector3.new(cx + 1, 6.5, fz + 9), Vector3.new(cx - 0.5, 3, cz - 2.5))
end

-- Floating numbers over the rooftops and the square (shot 18)
local sky = Instance.new("Folder")
sky.Name = "SkyNumbers"
sky.Parent = workspace
local rng = Random.new(18)
for i = 1, 26 do
	local pos = if i <= 16
		then Vector3.new(rng:NextNumber(-85, 85), rng:NextNumber(19, 27), rng:NextNumber(-96, -76))
		else Vector3.new(rng:NextNumber(-40, 40), rng:NextNumber(12, 20), rng:NextNumber(-40, 40))
	local anchor = part(sky, `Sky_{i}`, Vector3.new(1, 1, 1), CFrame.new(pos), Color3.new(1, 1, 1))
	anchor.Transparency = 1
	anchor.CanCollide = false
	anchor.CanQuery = false
end

-- A film set should load everything at once; streaming left far parts (the sky numbers) missing.
workspace.StreamingEnabled = false

return `Extras built: {#crowd:GetChildren()} crowd rigs, {#props:GetChildren()} props, bedroom set, {#sky:GetChildren()} sky anchors.`
