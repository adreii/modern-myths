--!strict
-- Read every avatar in the place (any Model with a Humanoid) into the JSON that
-- lib/imported.py repaints the shared Blender body from. Run it through the Studio MCP
-- (execute_luau) or the command bar, and save what it returns as assets/roblox/avatars.json.
-- Read-only: it changes nothing in the place.
--
-- Per avatar: body colours (sRGB 0-1, keyed like the Blender rig), model scale, height in
-- studs, rig type, and the face decal's texture id if it has one. "face" is left out when
-- the head has no decal, so the episode's cast.yaml `faces:` (or "neutral") decides.

local HttpService = game:GetService("HttpService")

local PARTS = {
	head = "HeadColor3",
	torso = "TorsoColor3",
	arm_l = "LeftArmColor3",
	arm_r = "RightArmColor3",
	leg_l = "LeftLegColor3",
	leg_r = "RightLegColor3",
}

local function rgb(c: Color3): { number }
	local function r(v: number): number
		return math.floor(v * 1000 + 0.5) / 1000
	end
	return { r(c.R), r(c.G), r(c.B) }
end

local avatars = {}
for _, root in { workspace, game:GetService("ReplicatedStorage"), game:GetService("ServerStorage") } do
	for _, m in root:GetDescendants() do
		local hum = m:IsA("Model") and m:FindFirstChildOfClass("Humanoid")
		if not hum then
			continue
		end
		local colors = {}
		local bc = m:FindFirstChildOfClass("BodyColors")
		if bc then
			for key, prop in PARTS do
				colors[key] = rgb((bc :: any)[prop])
			end
		end
		local entry: { [string]: any } = {
			path = m:GetFullName(),
			rig = hum.RigType.Name,
			scale = m:GetScale(),
			height = math.floor(m:GetExtentsSize().Y * 100 + 0.5) / 100,
			colors = colors,
		}
		local head = m:FindFirstChild("Head")
		local decal = head and head:FindFirstChildOfClass("Decal")
		if decal then
			entry.face_texture = decal.Texture
		end
		if avatars[m.Name] then
			warn("DumpAvatars: two avatars named " .. m.Name .. "; keeping " .. avatars[m.Name].path)
		else
			avatars[m.Name] = entry
		end
	end
end

return HttpService:JSONEncode(avatars)
