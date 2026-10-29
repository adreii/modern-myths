-- EP01_Shots (LocalScript in StarterPlayer > StarterPlayerScripts)
-- All 18 shots of EP01 "Everyone Has a Number" (see ep01-shot-list.md), blocked out with
-- placeholder acting from StoryKit/Puppet. Play starts in free mode: walk and look around as usual.
-- Click in the game view, then:
--   P   play all 18 shots back to back (one take for recording, about 62 s)
--   N   next shot          B   previous shot          R   replay the current shot
--   F   back to free mode (your character and the normal camera)
-- Shot keys switch to recording mode: Roblox UI hidden, your avatar parked out of frame.
-- Every shot sets up its own scene first, so any shot can be played on its own.
-- Needs BuildEP01Map, BuildEP01Extras, BuildTownPhase1 and BuildInteriorsPhase2 run in Edit mode.
-- Camera plan (lens, angle, power flip, contrast/affinity) is in ep01-shot-list.md.

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local StarterGui = game:GetService("StarterGui")
local UserInputService = game:GetService("UserInputService")

local StoryKit = ReplicatedStorage:WaitForChild("StoryKit")
local CameraRig = require(StoryKit:WaitForChild("CameraRig"))
local Light = require(StoryKit:WaitForChild("LightingPresets"))
local NumberBillboard = require(StoryKit:WaitForChild("NumberBillboard"))
local Puppet = require(StoryKit:WaitForChild("Puppet"))
local Sets = require(StoryKit:WaitForChild("Sets"))
local Lighting = game:GetService("Lighting")
local town = workspace:WaitForChild("Town")
local heroHouse = town:WaitForChild("Buildings"):WaitForChild("HeroHouse")

local hero = workspace:WaitForChild("Hero") :: Model
local baker = workspace:WaitForChild("Baker") :: Model
local influencer = workspace:WaitForChild("Influencer") :: Model
local crowdFolder = workspace:WaitForChild("Crowd")
local kid = crowdFolder:WaitForChild("Kid") :: Model
local props = workspace:WaitForChild("Props")
local markers = workspace:WaitForChild("Markers")
local skyFolder = workspace:WaitForChild("SkyNumbers")
local map = workspace:WaitForChild("EP01_Map")
local bakery = map:WaitForChild("BakeryStreet"):WaitForChild("Bakery") :: Model
local bakerHouse = map:WaitForChild("BakerHouse"):WaitForChild("BakerHouse") :: Model
local bedroom = map:WaitForChild("BakerBedroom") :: Model

local crowd: { Model } = {}
for i = 1, 7 do
	table.insert(crowd, crowdFolder:WaitForChild(`Crowd_{i}`) :: Model)
end

local bread: { BasePart } = {}
for i = 1, 4 do
	bread[i] = props:WaitForChild(`Bread_{i}`) :: BasePart
end
local basket = props:WaitForChild("Basket") :: BasePart
local bag = props:WaitForChild("BreadBag") :: BasePart
local phone = props:WaitForChild("Phone") :: BasePart
local bakeryWindow = bakery:WaitForChild("Window_1") :: BasePart
local bakeryLight = bakeryWindow:WaitForChild("BakeryLight") :: PointLight
local bakerDoor = bakerHouse:WaitForChild("Door") :: BasePart
local mattress = bedroom:WaitForChild("Mattress") :: BasePart

local function head(m: Model): BasePart
	return m:WaitForChild("Head") :: BasePart
end
local function markerPos(name: string): Vector3
	return (markers:WaitForChild(name) :: BasePart).Position
end

-- Ground heights (top surfaces)
local PLAZA = 0.55
local SIDEWALK = 0.9
local STEP = 0.8

local HERO_HOME = Vector3.new(12, PLAZA, 14)
local INFLUENCER_HOME = Vector3.new(-8, PLAZA, 6)
local KID_HOME = Vector3.new(-8, PLAZA, 15)
local BAKER_HOME = Vector3.new(-71, STEP, -69.5)
local BAKER_DOOR = Vector3.new(75, STEP, -68.6) -- where the Hero stands to knock
local OFFSTAGE = Vector3.new(0, PLAZA, 200)

local function ring(center: Vector3, radius: number, i: number, n: number): Vector3
	local a = (i / n) * math.pi * 2 + 0.4
	return center + Vector3.new(math.cos(a) * radius, 0, math.sin(a) * radius)
end

-- Recording mode: no Roblox UI, and park the player's own avatar out of frame.
local recording = false
local freeSpot: CFrame? = nil

local function setRecording(on: boolean)
	if on == recording then
		return
	end
	recording = on
	pcall(function()
		StarterGui:SetCoreGuiEnabled(Enum.CoreGuiType.All, not on)
	end)
	local character = Players.LocalPlayer.Character
	local root = character and character:FindFirstChild("HumanoidRootPart") :: BasePart?
	if on then
		if character and root then
			freeSpot = character:GetPivot()
			root.Anchored = true
			character:PivotTo(CFrame.new(0, 800, 0))
		end
		CameraRig.take()
	else
		if character and root then
			character:PivotTo(freeSpot or CFrame.new(0, 4, 40))
			root.Anchored = false
		end
		CameraRig.release()
		local humanoid = character and character:FindFirstChildOfClass("Humanoid")
		if humanoid then
			workspace.CurrentCamera.CameraSubject = humanoid
		end
	end
end

-- Register every rig while it still stands idle, then give everyone their number.
for _, m in { hero, baker, influencer, kid, table.unpack(crowd) } do
	Puppet.register(m)
end
local heroTag = NumberBillboard.attach(hero, { value = 212 })
local bakerTag = NumberBillboard.attach(baker, { value = 9 })
NumberBillboard.attach(influencer, { value = 50000, size = 7 })
local rng = Random.new(7)
for _, m in crowd do
	NumberBillboard.attach(m, { value = rng:NextInteger(40, 3000) })
end
NumberBillboard.attach(kid, { value = 57, size = 4, height = 2.4 })
local skyTags = {}
for i = 1, 26 do
	local anchor = skyFolder:WaitForChild(`Sky_{i}`)
	local tag = NumberBillboard.attach(anchor, { value = rng:NextInteger(3, 90000), size = 9, height = 0 })
	tag.gui.MaxDistance = 1000
	tag.gui.Enabled = false
	table.insert(skyTags, tag)
end

local function bakeryLit(on: boolean)
	bakeryLight.Enabled = on
	bakeryWindow.Material = if on then Enum.Material.Neon else Enum.Material.Glass
	bakeryWindow.Color = if on then Color3.fromRGB(255, 200, 120) else Color3.fromRGB(35, 45, 60)
end

local function doorOpen(open: boolean)
	bakerDoor.Color = if open then Color3.fromRGB(15, 12, 10) else Color3.fromRGB(110, 70, 45)
	bakerDoor.Material = if open then Enum.Material.SmoothPlastic else Enum.Material.Wood
end

-- Long-lens focus: Roblox cameras have no depth of field, so fake it per shot.
local dof = (Lighting:FindFirstChild("StoryKit_DOF") or Instance.new("DepthOfFieldEffect")) :: DepthOfFieldEffect
dof.Name = "StoryKit_DOF"
dof.Enabled = false
dof.Parent = Lighting
local function focus(distance: number, radius: number, far: number)
	dof.FocusDistance = distance
	dof.InFocusRadius = radius
	dof.FarIntensity = far
	dof.NearIntensity = 0
	dof.Enabled = true
end

-- The landing: every window in town glows warm, the real value finally outshining the yellow numbers.
local windows: { BasePart } = {}
for _, d in workspace:GetDescendants() do
	if d:IsA("BasePart") and d ~= bakeryWindow and (d:GetAttribute("StoryKitWindow") or (d.Name == "Glass" and d:IsDescendantOf(town))) then
		table.insert(windows, d)
	end
end
local function windowsWarm(on: boolean)
	for _, w in windows do
		if w:GetAttribute("WinMaterial") == nil then
			w:SetAttribute("WinMaterial", w.Material.Name)
			w:SetAttribute("WinColor", w.Color)
			w:SetAttribute("WinTransparency", w.Transparency)
		end
		if on then
			w.Material = Enum.Material.Neon
			w.Color = Color3.fromRGB(255, 200, 120)
			w.Transparency = 0.15
		else
			w.Material = (Enum.Material :: any)[w:GetAttribute("WinMaterial")]
			w.Color = w:GetAttribute("WinColor")
			w.Transparency = w:GetAttribute("WinTransparency")
		end
	end
end

-- Reset everything to the default layout. Each shot calls this first.
local function stage(light: string)
	Light.apply(light)
	Sets.reset()
	dof.Enabled = false
	windowsWarm(false)
	for _, m in { hero, baker, influencer, kid, table.unpack(crowd) } do
		Puppet.tap(m, false)
		Puppet.pose(m, "idle", 0)
	end
	Puppet.place(hero, HERO_HOME, Vector3.zAxis)
	Puppet.place(influencer, INFLUENCER_HOME, Vector3.zAxis)
	Puppet.place(kid, KID_HOME, -Vector3.zAxis)
	Puppet.place(baker, BAKER_HOME, Vector3.zAxis)
	for i, m in crowd do
		local spot = ring(Vector3.new(0, PLAZA, 0), 22, i, #crowd)
		Puppet.place(m, spot, -spot * Vector3.new(1, 0, 1))
	end
	heroTag:set(212)
	heroTag:dim(0, 0)
	bakerTag:dim(0, 0)
	for _, loaf in bread do
		loaf.Transparency = 1
	end
	Puppet.release(basket)
	Puppet.release(bag)
	Puppet.release(phone)
	bakeryLit(true)
	doorOpen(false)
	for _, tag in skyTags do
		tag.gui.Enabled = false
	end
end

local function heroHead(): Vector3
	return head(hero).Position
end
-- Aim a little above the head so the floating number stays in frame.
local function aboveHead(m: Model): Vector3
	return head(m).Position + Vector3.new(0, 1.8, 0)
end
local function later(delay: number, fn: () -> ())
	task.delay(delay, fn)
end

-- Shots 06 and 13 share this framing: looking down the row of doorsteps from above the bakery end.
local ROW_CAM = Vector3.new(-66, 5, -63)
local ROW_LOOK = Vector3.new(0, 0.8, -69.5)

local SHOTS: { { name: string, duration: number, play: () -> () } } = {
	{
		name = "01 everyone has a number",
		duration = 3.0,
		play = function()
			stage("dawn")
			heroTag:dim(1, 0)
			heroTag:dim(0, 1.6)
			local h = heroHead()
			CameraRig.play({
				kind = "push_in", duration = 3, fov = 40, fovTo = 36,
				from = { pos = h + Vector3.new(0, -2, 14), look = aboveHead(hero) },
				to = { pos = h + Vector3.new(0, -1, 9), look = aboveHead(hero) },
			})
		end,
	},
	{
		name = "02 nobody remembers",
		duration = 3.0,
		play = function()
			stage("day")
			-- 24 mm crane down into the square: the whole rule at once, the Town Hall clock behind it.
			CameraRig.play({
				kind = "crane", duration = 3, fov = 70,
				from = { pos = Vector3.new(0, 70, -40), look = Vector3.new(0, 4, 30) },
				to = { pos = Vector3.new(6, 16, -26), look = Vector3.new(0, 6, 40) },
			})
		end,
	},
	{
		name = "03 mine was 212",
		duration = 2.5,
		play = function()
			stage("day")
			later(0.3, function() Puppet.pose(hero, "look_up", 0.4) end)
			later(1.4, function() Puppet.pose(hero, "shrug", 0.3) end)
			local h = heroHead()
			-- High angle: the myth makes him small.
			CameraRig.play({ kind = "static", duration = 2.5, fov = 54, from = { pos = h + Vector3.new(0, 7, 9), look = h + Vector3.new(0, 0.5, 0) } })
		end,
	},
	{
		name = "04 the baker had 9",
		duration = 3.0,
		play = function()
			stage("pre_dawn_dark")
			Puppet.place(baker, Vector3.new(-62, SIDEWALK, -67), Vector3.xAxis)
			Puppet.hold(baker, basket)
			Puppet.pose(baker, "carry", 0)
			task.spawn(Puppet.walkTo, baker, Vector3.new(-4, SIDEWALK, -67), 3)
			CameraRig.play({
				kind = "pan", duration = 3, fov = 55, ease = "Linear",
				from = { pos = Vector3.new(-62, 5, -54), look = head(baker) },
				to = { pos = Vector3.new(-6, 5, -54), look = head(baker) },
			})
		end,
	},
	{
		name = "05 before anyone woke up",
		duration = 3.5,
		play = function()
			stage("pre_dawn_dark")
			Puppet.place(baker, Vector3.new(-17, SIDEWALK, -67.5), -Vector3.zAxis)
			Puppet.hold(baker, basket)
			Puppet.pose(baker, "carry", 0)
			later(0.2, function() Puppet.pose(baker, "crouch", 0.4) end)
			later(1.0, function() bread[2].Transparency = 0 end)
			later(1.6, function()
				Puppet.pose(baker, "carry", 0.3)
				Puppet.walkTo(baker, Vector3.new(6, SIDEWALK, -66.5), 1.8)
			end)
			CameraRig.play({
				kind = "pan", duration = 3.5, fov = 45,
				from = { pos = Vector3.new(-7.5, 3.2, -59.5), look = Vector3.new(-15, 1.8, -69) },
				to = { pos = Vector3.new(-7, 3, -61), look = head(baker) },
			})
		end,
	},
	{
		name = "06 bread on every doorstep",
		duration = 3.0,
		play = function()
			stage("dawn")
			for _, loaf in bread do
				loaf.Transparency = 0
			end
			CameraRig.play({
				kind = "crane", duration = 3, fov = 50, roll = 0, rollTo = 8,
				from = { pos = ROW_CAM, look = ROW_LOOK },
				to = { pos = ROW_CAM, look = ROW_LOOK },
			})
		end,
	},
	{
		name = "07 the guy with 50,000",
		duration = 3.0,
		play = function()
			stage("day")
			-- Low-angle 24 mm orbit, the shop row behind him: the centre of his own world.
			Puppet.place(influencer, INFLUENCER_HOME, -Vector3.xAxis)
			Puppet.pose(influencer, "flex", 0.4)
			CameraRig.play({ kind = "orbit", duration = 3, fov = 74, center = head(influencer), radius = 7, height = -2.5, startAngle = 160, endAngle = 200 })
		end,
	},
	{
		name = "08 busy making his number go up",
		duration = 2.5,
		play = function()
			stage("day")
			Puppet.hold(influencer, phone, "RightHand", CFrame.new(0, -0.4, -0.3) * CFrame.Angles(math.rad(-60), 0, 0))
			Puppet.pose(influencer, "phone", 0)
			later(0.2, function() Puppet.pose(kid, "wave", 0.3) end)
			local k = head(kid).Position
			CameraRig.play({ kind = "static", duration = 2.5, fov = 40, from = { pos = k + Vector3.new(1.6, 1.2, 4.5), look = head(influencer) } })
		end,
	},
	{
		name = "09 so I did what everyone does",
		duration = 3.0,
		play = function()
			stage("day")
			local h = heroHead()
			local look = aboveHead(hero)
			task.spawn(function()
				Puppet.turnTo(hero, head(influencer).Position, 0.4)
				task.wait(1.0)
				Puppet.turnTo(hero, HERO_HOME + Vector3.new(0, 0, 10), 0.4)
				Puppet.pose(hero, "look_up", 0.4)
			end)
			CameraRig.play({
				kind = "push_in", duration = 3, fov = 40,
				from = { pos = h + Vector3.new(0, -1, 14), look = look },
				to = { pos = h + Vector3.new(0, -0.5, 9), look = look },
			})
		end,
	},
	{
		name = "10 I started performing",
		duration = 2.0,
		play = function()
			stage("day")
			-- Rehearsing in his bedroom, the house opened like a dollhouse; 24 mm crash-zoomed to 50 mm.
			Sets.cutaway(heroHouse, true)
			Lighting.ExposureCompensation = -0.8 -- the open wall lets the noon sun flood the white room
			Puppet.place(hero, Vector3.new(122, 12.9, 126.5), -Vector3.zAxis)
			Puppet.pose(hero, "flex", 0.25)
			local h = heroHead()
			CameraRig.cut(Vector3.new(122, h.Y + 0.3, 104), h + Vector3.new(0, 0.8, 0), 70)
			task.wait(0.35)
			CameraRig.snapZoom(32, 0.12)
		end,
	},
	{
		name = "11 900, 3,000, 10,000",
		duration = 4.5,
		play = function()
			stage("day")
			Light.apply("dusk", 4.5)
			for i, m in crowd do
				task.spawn(function()
					Puppet.walkTo(m, ring(HERO_HOME, 9, i, #crowd), 2.2)
					Puppet.turnTo(m, HERO_HOME, 0.3)
				end)
			end
			task.spawn(function()
				Puppet.backflip(hero, 1.0)
				Puppet.pose(hero, "flex", 0.3)
				task.wait(1.4)
				Puppet.pose(hero, "wave", 0.3)
			end)
			task.spawn(function()
				CameraRig.play({ kind = "orbit", duration = 4.5, fov = 70, shake = 0.25, center = head(hero), radius = 9, height = -2.5, startAngle = 60, endAngle = 150 })
			end)
			for _, n in { 900, 3000, 10000 } do
				heroTag:countTo(n, 0.6)
				heroTag:pulse()
				task.wait(0.5)
			end
		end,
	},
	{
		name = "12 the fewer people knew my name",
		duration = 4.0,
		play = function()
			stage("dusk")
			heroTag:set(10000)
			Puppet.place(hero, HERO_HOME, -Vector3.xAxis)
			-- Clear the line of sight: the Hero must end up alone in the frame.
			Puppet.place(kid, OFFSTAGE)
			Puppet.place(influencer, OFFSTAGE + Vector3.new(6, 0, 0))
			for i, m in crowd do
				Puppet.place(m, ring(HERO_HOME, 9, i, #crowd), HERO_HOME - ring(HERO_HOME, 9, i, #crowd))
				if i > 1 then
					later(0.1 * i, function() Puppet.walkTo(m, ring(HERO_HOME, 48, i, #crowd), 2.0) end)
				end
			end
			-- One passer-by crosses between us and the Hero early, half-waving, and is gone by the second half.
			local passer = crowd[1]
			Puppet.place(passer, HERO_HOME + Vector3.new(-8, 0, -10), Vector3.zAxis)
			Puppet.pose(passer, "wave", 0.3)
			later(0.5, function() Puppet.walkTo(passer, HERO_HOME + Vector3.new(-8, 0, 14), 1.8) end)
			-- 135 mm from across the square, locked off: the Hero small and alone, the shops pressed flat behind.
			local h = heroHead()
			local cam = Vector3.new(-48, h.Y + 0.5, HERO_HOME.Z)
			focus((h - cam).Magnitude, 8, 0.5)
			CameraRig.play({ kind = "static", duration = 4, fov = 15, from = { pos = cam, look = h + Vector3.new(0, 1.2, 0) } })
		end,
	},
	{
		name = "13 no bread",
		duration = 3.5,
		play = function()
			stage("dawn")
			bakeryLit(false)
			CameraRig.play({ kind = "static", duration = 3.5, fov = 50, from = { pos = ROW_CAM, look = ROW_LOOK } })
		end,
	},
	{
		name = "14 the baker was sick",
		duration = 2.5,
		play = function()
			stage("dawn")
			Puppet.lie(baker, mattress.Position + Vector3.new(0.4, 0.3, 0), -Vector3.xAxis)
			bakerTag:dim(0.6, 0)
			local cam = markers:WaitForChild("Cam_BakerWindow") :: BasePart
			CameraRig.play({ kind = "static", duration = 2.5, fov = 45, from = { pos = cam.Position + Vector3.new(0, 2, 0), look = mattress.Position } })
		end,
	},
	{
		name = "15 no number could tell me that",
		duration = 3.5,
		play = function()
			stage("dawn")
			bakeryLit(false)
			for i, m in crowd do
				Puppet.place(m, Vector3.new(-36 + i * 11, SIDEWALK, -65), Vector3.zAxis)
			end
			-- His point of view, 135 mm down the line: every number stacked flat, none of them saying anything.
			Puppet.place(hero, Vector3.new(-84, SIDEWALK, -62.5), Vector3.xAxis) -- just behind the lens
			CameraRig.play({
				kind = "push_in", duration = 3.5, fov = 15, fovTo = 13, ease = "Sine",
				from = { pos = Vector3.new(-80, 6.8, -62.5), look = Vector3.new(20, 6.5, -65) },
				to = { pos = Vector3.new(-74, 6.8, -62.5), look = Vector3.new(20, 6.5, -65) },
			})
		end,
	},
	{
		name = "16 so I brought her bread",
		duration = 4.0,
		play = function()
			stage("dawn")
			heroTag:set(10000)
			-- Hero stands to the right of the door, so the camera on the left sees both of them.
			local spot = Vector3.new(77.4, STEP, -69)
			Puppet.place(hero, spot, Vector3.new(75, STEP, -71.6) - spot)
			Puppet.place(baker, OFFSTAGE)
			Puppet.hold(hero, bag, "LeftHand")
			Puppet.pose(hero, "knock", 0.2)
			Puppet.tap(hero, true)
			later(1.2, function() Puppet.tap(hero, false) Puppet.pose(hero, "hold_left", 0.2) end)
			later(1.4, function()
				doorOpen(true)
				Puppet.place(baker, Vector3.new(75, STEP, -71.4), spot - Vector3.new(75, STEP, -71.4))
			end)
			later(2.0, function() Puppet.pose(hero, "give", 0.4) end)
			later(2.7, function()
				Puppet.hold(baker, bag)
				Puppet.pose(baker, "carry", 0.3)
				Puppet.pose(hero, "idle", 0.4)
			end)
			-- Eye level, 50 mm: for the first time the Hero and someone else are equals in frame. Then an 85 mm insert on the hand-off.
			CameraRig.play({ kind = "static", duration = 2.3, fov = 40, from = { pos = Vector3.new(67.5, 5.2, -60.5), look = Vector3.new(76, 4.5, -70.5) } })
			CameraRig.play({ kind = "static", duration = 1.7, fov = 24, from = { pos = Vector3.new(71, 4.4, -64.5), look = Vector3.new(76, 4, -70.2) } })
		end,
	},
	{
		name = "17 not even by one",
		duration = 3.5,
		play = function()
			stage("dawn")
			heroTag:set(10000)
			Puppet.place(hero, BAKER_DOOR + Vector3.new(0, 0, 1.5), Vector3.zAxis)
			local h = heroHead()
			-- Eye level, 85 mm, background soft: the motif held still until it means nothing.
			focus(14, 4, 0.7)
			CameraRig.play({ kind = "static", duration = 3.5, fov = 24, from = { pos = h + Vector3.new(0, 1.6, 14), look = h + Vector3.new(0, 1.6, 0) } })
		end,
	},
	{
		name = "18 who was watching",
		duration = 6.0,
		play = function()
			stage("dawn")
			heroTag:set(10000)
			Puppet.place(hero, BAKER_DOOR + Vector3.new(0, 0, 1.5), Vector3.zAxis)
			for _, tag in skyTags do
				tag.gui.Enabled = true
			end
			windowsWarm(true)
			-- One slow big move: from eye level up to the whole town, every window lit warm under the numbers.
			local h = heroHead()
			CameraRig.play({
				kind = "crane", duration = 6, fov = 40, fovTo = 45, ease = "Sine",
				from = { pos = h + Vector3.new(0, 0.3, 9), look = h },
				to = { pos = markerPos("Cam_Town_Crane"), look = Vector3.new(0, 0, -40) },
			})
		end,
	},
}

local current = 0
local running = false

local function run(i: number)
	local shot = SHOTS[i]
	print(`[EP01] shot {shot.name} ({shot.duration}s)`)
	local t0 = os.clock()
	shot.play()
	local left = shot.duration - (os.clock() - t0)
	if left > 0 then
		task.wait(left)
	end
end

UserInputService.InputBegan:Connect(function(input, processed)
	if processed or running then
		return
	end
	local k = input.KeyCode
	local action: (() -> ())? = nil
	if k == Enum.KeyCode.P then
		action = function()
			for i = 1, #SHOTS do
				current = i
				run(i)
			end
			print("[EP01] done")
		end
	elseif k == Enum.KeyCode.F then
		setRecording(false)
		return
	elseif k == Enum.KeyCode.N then
		action = function()
			current = math.min(current + 1, #SHOTS)
			run(current)
		end
	elseif k == Enum.KeyCode.B then
		action = function()
			current = math.max(current - 1, 1)
			run(current)
		end
	elseif k == Enum.KeyCode.R then
		action = function()
			current = math.max(current, 1)
			run(current)
		end
	end
	if action then
		running = true
		setRecording(true)
		local ok, err = pcall(action)
		if not ok then
			warn(`[EP01] shot {current} failed: {err}`)
		end
		running = false
	end
end)

stage("dawn")
print("EP01_Shots ready (free mode): P plays all 18 shots, N/B next/previous, R replays, F returns to free mode.")
