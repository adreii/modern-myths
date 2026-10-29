--!strict
-- StoryKit/NumberBillboard
-- The glowing number that floats over a character's head (EP01 "Everyone Has a Number").
--
--   local NumberBillboard = require(ReplicatedStorage.StoryKit.NumberBillboard)
--   local tag = NumberBillboard.attach(workspace.Hero, { value = 212 })
--   tag:countTo(10000, 2.5)   -- ticks up like a counter, yields until done
--   tag:set(9)                -- instant
--   tag:dim(0.6)              -- 0 = full glow, 1 = gone (the baker is sick)
--   tag:pulse()               -- quick pop when the number changes
--   tag:destroy()
--
-- target: a character Model (uses its Head) or any BasePart.

local RunService = game:GetService("RunService")
local TweenService = game:GetService("TweenService")

export type Options = {
	value: number?,
	color: Color3?, -- number colour, default caption yellow
	glowColor: Color3?, -- halo colour, defaults to `color`
	height: number?, -- studs above the head, default 3.2
	size: number?, -- width in studs, default 6
	float: boolean?, -- gentle bob, default true
	alwaysOnTop: boolean?, -- show through walls, default false
}

local DEFAULT_COLOR = Color3.fromRGB(255, 210, 74)
local FONT = Font.fromEnum(Enum.Font.GothamBlack)

local NumberBillboard = {}
NumberBillboard.__index = NumberBillboard

export type Tag = typeof(setmetatable(
	{} :: {
		gui: BillboardGui,
		front: TextLabel,
		glow: TextLabel,
		glowStroke: UIStroke,
		frontStroke: UIStroke,
		value: number,
		baseHeight: number,
		dimAmount: number,
		connection: RBXScriptConnection?,
	},
	NumberBillboard
))

-- 10000 -> "10,000"
function NumberBillboard.format(n: number): string
	local s = tostring(math.floor(n + 0.5))
	local sign, digits = string.match(s, "^(%-?)(%d+)$")
	if not digits then
		return s
	end
	local withCommas = string.reverse((string.gsub(string.reverse(digits), "(%d%d%d)", "%1,")))
	withCommas = string.gsub(withCommas, "^,", "")
	return (sign or "") .. withCommas
end

local function makeLabel(name: string, color: Color3, parent: Instance): TextLabel
	local label = Instance.new("TextLabel")
	label.Name = name
	label.BackgroundTransparency = 1
	label.Size = UDim2.fromScale(1, 1)
	label.TextScaled = true
	label.FontFace = FONT
	label.TextColor3 = color
	label.Parent = parent
	return label
end

function NumberBillboard.attach(target: Instance, opts: Options?): Tag
	local o: Options = opts or {}
	local adornee: BasePart
	if target:IsA("Model") then
		local head = target:FindFirstChild("Head")
		adornee = (if head and head:IsA("BasePart") then head else target.PrimaryPart) :: BasePart
	else
		adornee = target :: BasePart
	end
	assert(adornee, `NumberBillboard: {target:GetFullName()} has no Head or PrimaryPart`)

	local color = o.color or DEFAULT_COLOR
	local width = o.size or 6
	local height = o.height or 3.2

	local gui = Instance.new("BillboardGui")
	gui.Name = "StoryKit_Number"
	gui.Adornee = adornee
	gui.Size = UDim2.fromScale(width, width / 3) -- scale units on a BillboardGui are studs
	gui.StudsOffset = Vector3.new(0, height, 0)
	gui.AlwaysOnTop = o.alwaysOnTop == true
	gui.LightInfluence = 0 -- glows at night instead of being darkened
	gui.MaxDistance = 400
	gui.Parent = adornee

	-- Back layer: soft halo made from a thick, faint stroke.
	local glow = makeLabel("Glow", color, gui)
	glow.TextTransparency = 0.6
	local glowStroke = Instance.new("UIStroke")
	glowStroke.Color = o.glowColor or color
	glowStroke.Thickness = 8
	glowStroke.Transparency = 0.75
	glowStroke.Parent = glow

	-- Front layer: crisp number with a dark outline, like the captions.
	local front = makeLabel("Number", color, gui)
	front.ZIndex = 2
	local frontStroke = Instance.new("UIStroke")
	frontStroke.Color = Color3.fromRGB(20, 20, 28)
	frontStroke.Thickness = 2.5
	frontStroke.Parent = front

	local self = setmetatable({
		gui = gui,
		front = front,
		glow = glow,
		glowStroke = glowStroke,
		frontStroke = frontStroke,
		value = 0,
		baseHeight = height,
		dimAmount = 0,
		connection = nil :: RBXScriptConnection?,
	}, NumberBillboard)

	self:set(o.value or 0)

	if o.float ~= false then
		local phase = math.random() * math.pi * 2
		self.connection = RunService.Heartbeat:Connect(function()
			local t = os.clock()
			gui.StudsOffset = Vector3.new(0, self.baseHeight + math.sin(t * 1.6 + phase) * 0.15, 0)
		end)
	end

	gui.Destroying:Connect(function()
		if self.connection then
			self.connection:Disconnect()
		end
	end)

	return self
end

function NumberBillboard.set(self: Tag, value: number)
	self.value = value
	local text = NumberBillboard.format(value)
	self.front.Text = text
	self.glow.Text = text
end

-- Count from the current value to `target` over `duration` seconds. Yields.
function NumberBillboard.countTo(self: Tag, target: number, duration: number?, easing: Enum.EasingStyle?)
	local from = self.value
	local time = math.max(duration or 1.5, 0.05)
	local style = easing or Enum.EasingStyle.Quad
	local elapsed = 0
	while elapsed < time do
		elapsed += RunService.Heartbeat:Wait()
		local a = TweenService:GetValue(math.clamp(elapsed / time, 0, 1), style, Enum.EasingDirection.Out)
		self:set(from + (target - from) * a)
	end
	self:set(target)
end

-- 0 = full glow, 1 = invisible.
function NumberBillboard.dim(self: Tag, amount: number, duration: number?)
	self.dimAmount = math.clamp(amount, 0, 1)
	local d = self.dimAmount
	local info = TweenInfo.new(duration or 0.6, Enum.EasingStyle.Sine)
	TweenService:Create(self.front, info, { TextTransparency = d }):Play()
	TweenService:Create(self.frontStroke, info, { Transparency = d }):Play()
	TweenService:Create(self.glow, info, { TextTransparency = 0.6 + 0.4 * d }):Play()
	TweenService:Create(self.glowStroke, info, { Transparency = 0.75 + 0.25 * d }):Play()
end

-- Quick scale pop, for each tick in a montage.
function NumberBillboard.pulse(self: Tag, strength: number?)
	local s = strength or 1.25
	local base = self.gui.Size
	local big = UDim2.fromScale(base.X.Scale * s, base.Y.Scale * s)
	local up = TweenService:Create(self.gui, TweenInfo.new(0.08, Enum.EasingStyle.Quad, Enum.EasingDirection.Out), { Size = big })
	up:Play()
	up.Completed:Wait()
	TweenService:Create(self.gui, TweenInfo.new(0.25, Enum.EasingStyle.Back, Enum.EasingDirection.Out), { Size = base }):Play()
end

function NumberBillboard.destroy(self: Tag)
	if self.connection then
		self.connection:Disconnect()
		self.connection = nil
	end
	self.gui:Destroy()
end

return NumberBillboard
