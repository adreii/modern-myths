--!strict
-- StoryKit/LightingPresets
-- Named moods for time of day. Works from a LocalScript (recording) or a Script.
--
--   local Light = require(ReplicatedStorage.StoryKit.LightingPresets)
--   Light.apply("dawn")            -- snap
--   Light.apply("dusk", 4)         -- fade over 4 seconds (doesn't yield)
--   Light.apply("night", 3, true)  -- fade and wait for it to finish
--
-- Time always moves forward: night (21) -> dawn (6.4) runs through midnight
-- rather than rewinding through the afternoon.
-- Tune the values in PRESETS once against your own map, then keep them fixed so every episode matches.

local Lighting = game:GetService("Lighting")
local TweenService = game:GetService("TweenService")

type Preset = {
	clockTime: number,
	brightness: number,
	exposure: number,
	ambient: Color3,
	outdoorAmbient: Color3,
	atmosphere: { density: number, haze: number, color: Color3, decay: Color3 },
	grade: { tint: Color3, saturation: number, contrast: number, brightness: number },
	bloom: { intensity: number, size: number, threshold: number },
}

local PRESETS: { [string]: Preset } = {
	pre_dawn_dark = {
		clockTime = 6.0, brightness = 1.1, exposure = -0.05,
		ambient = Color3.fromRGB(85, 95, 130), outdoorAmbient = Color3.fromRGB(110, 120, 160),
		atmosphere = { density = 0.35, haze = 1.5, color = Color3.fromRGB(130, 145, 185), decay = Color3.fromRGB(70, 80, 120) },
		grade = { tint = Color3.fromRGB(195, 210, 255), saturation = -0.25, contrast = 0.1, brightness = -0.02 },
		bloom = { intensity = 0.9, size = 28, threshold = 0.9 },
	},
	dawn = {
		clockTime = 6.4, brightness = 1.6, exposure = 0,
		ambient = Color3.fromRGB(90, 80, 90), outdoorAmbient = Color3.fromRGB(140, 120, 120),
		atmosphere = { density = 0.33, haze = 2, color = Color3.fromRGB(255, 205, 170), decay = Color3.fromRGB(140, 120, 150) },
		grade = { tint = Color3.fromRGB(255, 236, 220), saturation = 0.05, contrast = 0.08, brightness = 0 },
		bloom = { intensity = 0.6, size = 30, threshold = 0.85 },
	},
	day = {
		clockTime = 13, brightness = 2.4, exposure = 0,
		ambient = Color3.fromRGB(110, 110, 120), outdoorAmbient = Color3.fromRGB(150, 150, 160),
		atmosphere = { density = 0.25, haze = 0.5, color = Color3.fromRGB(200, 220, 255), decay = Color3.fromRGB(110, 130, 160) },
		grade = { tint = Color3.fromRGB(255, 255, 255), saturation = 0.15, contrast = 0.1, brightness = 0 },
		bloom = { intensity = 0.35, size = 24, threshold = 0.95 },
	},
	dusk = {
		clockTime = 18.5, brightness = 1.4, exposure = -0.1,
		ambient = Color3.fromRGB(95, 70, 80), outdoorAmbient = Color3.fromRGB(140, 100, 100),
		atmosphere = { density = 0.32, haze = 2.2, color = Color3.fromRGB(255, 170, 120), decay = Color3.fromRGB(120, 80, 120) },
		grade = { tint = Color3.fromRGB(255, 225, 205), saturation = 0.1, contrast = 0.12, brightness = -0.02 },
		bloom = { intensity = 0.7, size = 32, threshold = 0.85 },
	},
	night = {
		clockTime = 21, brightness = 0.4, exposure = -0.4,
		ambient = Color3.fromRGB(30, 35, 60), outdoorAmbient = Color3.fromRGB(45, 50, 85),
		atmosphere = { density = 0.36, haze = 1, color = Color3.fromRGB(80, 95, 140), decay = Color3.fromRGB(40, 45, 80) },
		grade = { tint = Color3.fromRGB(190, 205, 255), saturation = -0.2, contrast = 0.15, brightness = -0.04 },
		bloom = { intensity = 1.1, size = 30, threshold = 0.8 }, -- makes neon eyes and glowing numbers pop
	},
}

local LightingPresets = {}
LightingPresets.PRESETS = PRESETS

-- StoryKit owns one of each effect so presets never fight a map's own effects.
local function ensure<T>(className: string, name: string): T
	local existing = Lighting:FindFirstChild(name)
	if existing then
		return existing :: any
	end
	local inst = Instance.new(className)
	inst.Name = name
	inst.Parent = Lighting
	return inst :: any
end

local clockDriver = Instance.new("NumberValue")
clockDriver.Changed:Connect(function(v)
	Lighting.ClockTime = v % 24
end)

-- Apply a preset by name. duration 0 (default) snaps; wait = true yields until the fade ends.
function LightingPresets.apply(name: string, duration: number?, wait: boolean?)
	local p = PRESETS[name]
	assert(p, `LightingPresets: no preset called "{name}"`)
	local time = duration or 0

	local atmosphere = ensure("Atmosphere", "StoryKit_Atmosphere") :: Atmosphere
	local grade = ensure("ColorCorrectionEffect", "StoryKit_Grade") :: ColorCorrectionEffect
	local bloom = ensure("BloomEffect", "StoryKit_Bloom") :: BloomEffect

	-- Always move the clock forward.
	local from = Lighting.ClockTime
	local target = p.clockTime
	if target < from then
		target += 24
	end
	clockDriver.Value = from

	local targets: { [Instance]: { [string]: any } } = {
		[Lighting] = {
			Brightness = p.brightness,
			ExposureCompensation = p.exposure,
			Ambient = p.ambient,
			OutdoorAmbient = p.outdoorAmbient,
		},
		[clockDriver] = { Value = target },
		[atmosphere] = {
			Density = p.atmosphere.density,
			Haze = p.atmosphere.haze,
			Color = p.atmosphere.color,
			Decay = p.atmosphere.decay,
		},
		[grade] = {
			TintColor = p.grade.tint,
			Saturation = p.grade.saturation,
			Contrast = p.grade.contrast,
			Brightness = p.grade.brightness,
		},
		[bloom] = { Intensity = p.bloom.intensity, Size = p.bloom.size, Threshold = p.bloom.threshold },
	}

	if time <= 0 then
		for inst, props in targets do
			for prop, value in props do
				(inst :: any)[prop] = value
			end
		end
		return
	end

	local info = TweenInfo.new(time, Enum.EasingStyle.Sine, Enum.EasingDirection.InOut)
	local last: Tween? = nil
	for inst, props in targets do
		local tween = TweenService:Create(inst, info, props)
		tween:Play()
		last = tween
	end
	if wait and last then
		last.Completed:Wait()
	end
end

return LightingPresets
