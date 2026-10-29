--!strict
-- StoryKit/Puppet
-- Placeholder acting for R15 rigs until hand-made Moon Animator moves replace it. Client-only.
-- Rigs keep an anchored HumanoidRootPart: Puppet moves the whole model with PivotTo and bends
-- limbs by writing each joint's Transform every frame (Motor6D on older rigs, AnimationConstraint
-- on the rigs Studio creates now).
--
--   Puppet.place(workspace.Baker, Vector3.new(-15, 0.9, -70), Vector3.zAxis) -- feet on that ground point, facing +Z
--   Puppet.pose(workspace.Baker, "crouch", 0.4)                  -- blend into a pose (doesn't yield)
--   Puppet.walkTo(workspace.Baker, Vector3.new(15, 0.9, -70), 2) -- yields while walking
--   Puppet.backflip(workspace.Hero, 1)
--   Puppet.hold(workspace.Baker, workspace.Props.Basket)         -- weld a prop to a hand

local RunService = game:GetService("RunService")
local TweenService = game:GetService("TweenService")

local Puppet = {}

local function rx(deg: number): CFrame
	return CFrame.Angles(math.rad(deg), 0, 0)
end
local function rz(deg: number): CFrame
	return CFrame.Angles(0, 0, math.rad(deg))
end

-- Joint rotations in each joint's own frame. +X on a shoulder or hip swings the limb forward,
-- +Z on the right shoulder lifts that arm out to the side (-Z for the left), +X on the neck looks up.
Puppet.POSES = {
	idle = {},
	look_up = { Neck = rx(28) },
	look_down = { Neck = rx(-25) },
	shrug = { LeftShoulder = rz(-25), RightShoulder = rz(25), LeftElbow = rx(80), RightElbow = rx(80), Neck = rz(10) },
	wave = { RightShoulder = rz(150), RightElbow = rz(25) },
	flex = { LeftShoulder = rz(-90), RightShoulder = rz(90), LeftElbow = rz(-95), RightElbow = rz(95), Neck = rx(10) },
	crouch = {
		Root = CFrame.new(0, -1.3, 0), Waist = rx(-30),
		LeftHip = rx(80), RightHip = rx(80), LeftKnee = rx(-110), RightKnee = rx(-110),
		RightShoulder = rx(55), LeftShoulder = rx(35),
	},
	tuck = { LeftHip = rx(100), RightHip = rx(100), LeftKnee = rx(-120), RightKnee = rx(-120), LeftShoulder = rx(60), RightShoulder = rx(60) },
	carry = { RightShoulder = rx(25), RightElbow = rx(70) },
	phone = { RightShoulder = rx(45), RightElbow = rx(85), Neck = rx(-30) },
	knock = { RightShoulder = rx(95), RightElbow = rx(50), LeftElbow = rx(60) },
	give = { LeftShoulder = rx(80), LeftElbow = rx(10) },
	hold_left = { LeftElbow = rx(60) },
}

type State = {
	motors: { [string]: any }, -- Motor6D or AnimationConstraint, both expose Transform
	from: { [string]: CFrame },
	to: { [string]: CFrame },
	t0: number,
	dur: number,
	walking: boolean,
	walkT: number,
	tap: boolean,
	hipOffset: number,
}

local states: { [Model]: State } = {}

-- First call per model must happen while it stands in its idle pose, so the foot offset is right.
local function stateOf(model: Model): State
	local s = states[model]
	if s then
		return s
	end
	local motors = {}
	for _, d in model:GetDescendants() do
		if d:IsA("Motor6D") or d:IsA("AnimationConstraint") then
			motors[d.Name] = d
		end
	end
	local cf, size = model:GetBoundingBox()
	s = {
		motors = motors,
		from = {},
		to = {},
		t0 = 0,
		dur = 0,
		walking = false,
		walkT = 0,
		tap = false,
		hipOffset = model:GetPivot().Y - (cf.Y - size.Y / 2),
	}
	states[model] = s
	return s
end

local function blended(s: State, name: string): CFrame
	local a = if s.dur > 0 then math.clamp((os.clock() - s.t0) / s.dur, 0, 1) else 1
	a = TweenService:GetValue(a, Enum.EasingStyle.Sine, Enum.EasingDirection.InOut)
	return (s.from[name] or CFrame.identity):Lerp(s.to[name] or CFrame.identity, a)
end

RunService.RenderStepped:Connect(function(dt)
	for model, s in states do
		if not model.Parent then
			states[model] = nil
			continue
		end
		if s.walking then
			s.walkT += dt
		end
		local swing = if s.walking then math.sin(s.walkT * 9) else 0
		local tap = if s.tap then math.max(0, math.sin(os.clock() * 14)) else 0
		for name, motor in s.motors do
			local cf = blended(s, name)
			if s.walking then
				if name == "LeftHip" then
					cf *= rx(30 * swing)
				elseif name == "RightHip" then
					cf *= rx(-30 * swing)
				elseif name == "LeftShoulder" then
					cf *= rx(-25 * swing)
				elseif name == "RightShoulder" then
					cf *= rx(25 * swing)
				elseif name == "LeftKnee" or name == "RightKnee" then
					cf *= rx(-15 * math.abs(swing))
				end
			end
			if tap > 0 and name == "RightElbow" then
				cf *= rx(25 * tap)
			end
			motor.Transform = cf
		end
	end
end)

function Puppet.register(model: Model)
	stateOf(model)
end

-- Blend into a named pose over `duration` seconds (0 snaps). Doesn't yield.
function Puppet.pose(model: Model, name: string, duration: number?)
	local target = Puppet.POSES[name]
	assert(target, `Puppet: no pose called "{name}"`)
	local s = stateOf(model)
	local from = {}
	for jointName in s.motors do
		from[jointName] = blended(s, jointName)
	end
	s.from = from
	s.to = target
	s.t0 = os.clock()
	s.dur = duration or 0.3
end

-- Knocking: bounce the right forearm while on.
function Puppet.tap(model: Model, on: boolean)
	stateOf(model).tap = on
end

local function flat(v: Vector3): Vector3
	local f = Vector3.new(v.X, 0, v.Z)
	return if f.Magnitude > 1e-3 then f.Unit else Vector3.zAxis
end

-- Stand the model with its feet on `ground`, facing `facing` (default: keep current facing).
function Puppet.place(model: Model, ground: Vector3, facing: Vector3?)
	local s = stateOf(model)
	local dir = flat(facing or model:GetPivot().LookVector)
	local pos = ground + Vector3.new(0, s.hipOffset, 0)
	model:PivotTo(CFrame.lookAt(pos, pos + dir))
end

local function groundOf(model: Model): Vector3
	return model:GetPivot().Position - Vector3.new(0, stateOf(model).hipOffset, 0)
end

-- Turn in place to face a point. Yields for `duration`.
function Puppet.turnTo(model: Model, target: Vector3, duration: number?)
	local time = duration or 0.3
	local ground = groundOf(model)
	local fromDir = flat(model:GetPivot().LookVector)
	local toDir = flat(target - ground)
	local elapsed = 0
	while elapsed < time do
		elapsed += RunService.RenderStepped:Wait()
		local a = TweenService:GetValue(math.clamp(elapsed / time, 0, 1), Enum.EasingStyle.Sine, Enum.EasingDirection.InOut)
		Puppet.place(model, ground, fromDir:Lerp(toDir, a))
	end
	Puppet.place(model, ground, toDir)
end

-- Walk to a ground point over `duration` seconds, swinging arms and legs. Yields.
function Puppet.walkTo(model: Model, target: Vector3, duration: number)
	local s = stateOf(model)
	local from = groundOf(model)
	local dir = flat(target - from)
	s.walking = true
	local elapsed = 0
	while elapsed < duration do
		elapsed += RunService.RenderStepped:Wait()
		Puppet.place(model, from:Lerp(target, math.clamp(elapsed / duration, 0, 1)), dir)
	end
	s.walking = false
	Puppet.place(model, target, dir)
end

-- Jump, flip backwards once and land on the same spot. Yields.
function Puppet.backflip(model: Model, duration: number?)
	local time = duration or 1
	local base = model:GetPivot()
	Puppet.pose(model, "tuck", time * 0.2)
	local elapsed = 0
	while elapsed < time do
		elapsed += RunService.RenderStepped:Wait()
		local a = math.clamp(elapsed / time, 0, 1)
		local height = math.sin(a * math.pi) * 6
		model:PivotTo(base * CFrame.new(0, height, 0) * CFrame.Angles(a * math.pi * 2, 0, 0))
	end
	model:PivotTo(base)
	Puppet.pose(model, "idle", 0.2)
end

-- Lay the model on its back on `surface`, head pointing along `headDir`.
function Puppet.lie(model: Model, surface: Vector3, headDir: Vector3)
	stateOf(model)
	Puppet.pose(model, "idle", 0)
	local up = headDir.Unit
	local back = Vector3.new(0, -1, 0) -- local +Z (the back) faces down, so the face points at the sky
	local right = up:Cross(back)
	model:PivotTo(CFrame.fromMatrix(surface + Vector3.new(0, 0.6, 0), right, up, back))
end

-- Weld a prop to a hand. The rig's root is anchored, so the prop moves with the arm.
function Puppet.hold(model: Model, prop: BasePart, hand: string?, offset: CFrame?)
	local handPart = model:FindFirstChild(hand or "RightHand") :: BasePart?
	assert(handPart, `Puppet: {model.Name} has no {hand or "RightHand"}`)
	Puppet.release(prop)
	prop.Anchored = false
	prop.CanCollide = false
	prop.Massless = true
	prop.Transparency = 0
	prop.CFrame = handPart.CFrame * (offset or CFrame.new(0, -0.7, 0))
	local weld = Instance.new("WeldConstraint")
	weld.Name = "StoryKit_Hold"
	weld.Part0 = handPart
	weld.Part1 = prop
	weld.Parent = prop
end

-- Drop a held prop. With `at`, park it there; otherwise hide it.
function Puppet.release(prop: BasePart, at: CFrame?)
	local weld = prop:FindFirstChild("StoryKit_Hold")
	if weld then
		weld:Destroy()
	end
	prop.Anchored = true
	if at then
		prop.CFrame = at
	else
		prop.CFrame = CFrame.new(0, -60, 0)
	end
end

return Puppet
