--!strict
-- StoryKit/CameraRig
-- Scripted cinematic camera moves for recording shots. Client-only: require from a LocalScript.
--
--   local CameraRig = require(ReplicatedStorage.StoryKit.CameraRig)
--   CameraRig.take()
--   CameraRig.play({ kind = "push_in", duration = 3,
--       from = { pos = Vector3.new(0, 4, 20), look = "Hero.Head" },
--       to   = { pos = Vector3.new(0, 4, 8),  look = "Hero.Head" } })
--   CameraRig.release()
--
-- Targets (pos / look / center) can be a Vector3, CFrame, BasePart, Model, Attachment,
-- or a dot path under workspace such as "Markers.Cam_Square_A" or "Hero.Head".
-- Moving targets (a walking character's head) are re-read every frame.

local RunService = game:GetService("RunService")
local TweenService = game:GetService("TweenService")

export type Target = Vector3 | CFrame | Instance | string

export type Shot = {
	kind: string?, -- "static" | "push_in" | "pull_out" | "pan" | "crane" | "orbit" (all but orbit are from -> to)
	duration: number,
	from: { pos: Target?, look: Target? }?,
	to: { pos: Target?, look: Target? }?,
	-- orbit only
	center: Target?,
	radius: number?,
	height: number?,
	startAngle: number?, -- degrees
	endAngle: number?,
	-- shared
	fov: number?,
	fovTo: number?,
	ease: string?, -- Enum.EasingStyle name, default "Sine"
	direction: string?, -- Enum.EasingDirection name, default "InOut"
	shake: number?, -- handheld wobble in studs, 0 = locked off (0.1-0.3 reads as handheld)
	roll: number?, -- degrees of camera roll, for dutch angles
	rollTo: number?, -- animate the roll to this many degrees over the move
}

local CameraRig = {}

local camera = workspace.CurrentCamera

function CameraRig.find(path: string): Instance
	local node: Instance = workspace
	for name in string.gmatch(path, "[^%.]+") do
		local child = node:WaitForChild(name, 5)
		if not child then
			error(`CameraRig: can't find "{path}" (stopped at "{name}")`)
		end
		node = child
	end
	return node
end

local function resolveInstance(target: Target): Target
	if typeof(target) == "string" then
		return CameraRig.find(target)
	end
	return target
end

local function positionOf(target: Target): Vector3
	if typeof(target) == "Vector3" then
		return target
	elseif typeof(target) == "CFrame" then
		return target.Position
	elseif typeof(target) == "Instance" then
		if target:IsA("BasePart") then
			return target.Position
		elseif target:IsA("Model") then
			return target:GetPivot().Position
		elseif target:IsA("Attachment") then
			return target.WorldPosition
		end
	end
	error(`CameraRig: can't get a position from {tostring(target)}`)
end

-- Hand the camera over to scripts. Call once before the first shot.
function CameraRig.take()
	camera.CameraType = Enum.CameraType.Scriptable
end

-- Give the camera back to the player.
function CameraRig.release()
	camera.CameraType = Enum.CameraType.Custom
	camera.FieldOfView = 70
end

-- Jump straight to a framing with no move.
function CameraRig.cut(pos: Target, look: Target, fov: number?)
	camera.CFrame = CFrame.lookAt(positionOf(resolveInstance(pos)), positionOf(resolveInstance(look)))
	if fov then
		camera.FieldOfView = fov
	end
end

-- Play one camera move. Yields until it finishes; wrap in task.spawn to run alongside other actions.
function CameraRig.play(shot: Shot)
	local kind = shot.kind or "push_in"
	local duration = math.max(shot.duration, 0.05)
	local style = (Enum.EasingStyle :: any)[shot.ease or "Sine"]
	local direction = (Enum.EasingDirection :: any)[shot.direction or "InOut"]
	local shake = shot.shake or 0
	local roll = math.rad(shot.roll or 0)
	local rollTo = math.rad(shot.rollTo or shot.roll or 0)
	local fovFrom = shot.fov or camera.FieldOfView
	local fovTo = shot.fovTo or fovFrom

	local from = shot.from or {}
	local to = shot.to or from
	local fromPos = from.pos and resolveInstance(from.pos)
	local fromLook = from.look and resolveInstance(from.look)
	local toPos = (to.pos and resolveInstance(to.pos)) or fromPos
	local toLook = (to.look and resolveInstance(to.look)) or fromLook

	local center = shot.center and resolveInstance(shot.center)
	if kind == "orbit" then
		assert(center, "CameraRig: orbit needs a center")
	else
		assert(fromPos and fromLook, `CameraRig: "{kind}" needs from.pos and from.look`)
	end

	local seed = math.random() * 1000
	local elapsed = 0
	while elapsed < duration do
		elapsed += RunService.RenderStepped:Wait()
		local t = math.clamp(elapsed / duration, 0, 1)
		local a = if kind == "static" then 0 else TweenService:GetValue(t, style, direction)

		local pos: Vector3, look: Vector3
		if kind == "orbit" then
			local c = positionOf(center :: Target)
			local angle = math.rad((shot.startAngle or 0) + ((shot.endAngle or 90) - (shot.startAngle or 0)) * a)
			local r = shot.radius or 12
			pos = c + Vector3.new(math.cos(angle) * r, shot.height or 3, math.sin(angle) * r)
			look = c
		else
			pos = positionOf(fromPos :: Target):Lerp(positionOf(toPos :: Target), a)
			look = positionOf(fromLook :: Target):Lerp(positionOf(toLook :: Target), a)
		end

		if shake > 0 then
			local n = elapsed * 1.7
			pos += Vector3.new(math.noise(n, seed), math.noise(seed, n), math.noise(n, n + seed)) * shake
			look += Vector3.new(math.noise(n + 5, seed), math.noise(seed, n + 5), 0) * shake * 0.5
		end

		camera.CFrame = CFrame.lookAt(pos, look) * CFrame.Angles(0, 0, roll + (rollTo - roll) * a)
		camera.FieldOfView = fovFrom + (fovTo - fovFrom) * a
	end
end

-- Quick snap zoom (shot 10 in EP01): punch the FOV in over a few frames.
function CameraRig.snapZoom(fovTo: number, duration: number?)
	local tween = TweenService:Create(
		camera,
		TweenInfo.new(duration or 0.12, Enum.EasingStyle.Quad, Enum.EasingDirection.Out),
		{ FieldOfView = fovTo }
	)
	tween:Play()
	tween.Completed:Wait()
end

return CameraRig
