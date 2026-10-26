# Live Studio Playtest Probes (`execute_luau`)

Run these self-contained `--!strict` Luau probes with Studio MCP `execute_luau`.

---

## 1. UI, TouchGui & Highlight Probe (`datamodel_type: "Client"`)

Flags small targets, overlaps and large transparent active containers. Checks visible TouchGui JumpButton bounds when present. Rotation, occlusion, insets and input routing affect results: confirm hits and PlayerList/topbar conflicts manually. Client Highlight counts include disabled instances; Roblox documents a 255-slot limit ([Highlight](https://create.roblox.com/docs/reference/engine/classes/Highlight)). Confirm rendering visually, including client-created highlights.

```lua
--!strict
local Players = game:GetService("Players")
local player = Players.LocalPlayer
assert(player, "LocalPlayer missing; run in Client during Play")
local playerGui = player:WaitForChild("PlayerGui") :: PlayerGui
local camera = workspace.CurrentCamera
assert(camera, "Camera missing")
local viewport = camera.ViewportSize

type Box = { name: string, pos: Vector2, size: Vector2 }
local buttons: { Box } = {}
local small: { string } = {}
local overlaps: { string } = {}
local jumpHits: { string } = {}
local swallowing: { string } = {}

local function bounds(gui: GuiObject): (Vector2?, Vector2?)
	local lo = gui.AbsolutePosition
	local hi = lo + gui.AbsoluteSize
	local current: Instance? = gui
	while current and current ~= playerGui do
		if current:IsA("GuiObject") then
			if not current.Visible then
				return nil, nil
			end
			if current ~= gui and current.ClipsDescendants then
				local p = current.AbsolutePosition
				local q = p + current.AbsoluteSize
				lo = Vector2.new(math.max(lo.X, p.X), math.max(lo.Y, p.Y))
				hi = Vector2.new(math.min(hi.X, q.X), math.min(hi.Y, q.Y))
			end
		elseif current:IsA("LayerCollector") and not current.Enabled then
			return nil, nil
		end
		current = current.Parent
	end
	lo = Vector2.new(math.max(0, lo.X), math.max(0, lo.Y))
	hi = Vector2.new(math.min(viewport.X, hi.X), math.min(viewport.Y, hi.Y))
	if hi.X <= lo.X or hi.Y <= lo.Y then
		return nil, nil
	end
	return lo, hi - lo
end

local function area(a: Box, b: Box): number
	local x =
		math.max(0, math.min(a.pos.X + a.size.X, b.pos.X + b.size.X) - math.max(a.pos.X, b.pos.X))
	local y =
		math.max(0, math.min(a.pos.Y + a.size.Y, b.pos.Y + b.size.Y) - math.max(a.pos.Y, b.pos.Y))
	return x * y
end

local touchGui = playerGui:FindFirstChild("TouchGui")
local jump = if touchGui then touchGui:FindFirstChild("JumpButton", true) else nil
local jumpBox: Box? = nil
if jump and jump:IsA("GuiObject") then
	local pos, size = bounds(jump)
	if pos and size then
		jumpBox = { name = jump:GetFullName(), pos = pos, size = size }
	end
end

for _, inst in playerGui:GetDescendants() do
	if inst:IsA("GuiObject") and not (touchGui and inst:IsDescendantOf(touchGui)) then
		local pos, size = bounds(inst)
		if pos and size then
			if inst:IsA("GuiButton") and inst.Active then
				local box = { name = inst:GetFullName(), pos = pos, size = size }
				if size.X < 48 or size.Y < 48 then
					table.insert(small, box.name)
				end
				if jumpBox and area(box, jumpBox) > 16 then
					table.insert(jumpHits, box.name)
				end
				table.insert(buttons, box)
			elseif
				not inst:IsA("GuiButton")
				and inst.Active
				and inst.BackgroundTransparency > 0.9
			then
				if size.X * size.Y > viewport.X * viewport.Y * 0.25 then
					table.insert(swallowing, inst:GetFullName())
				end
			end
		end
	end
end
for i = 1, #buttons do
	for j = i + 1, #buttons do
		if area(buttons[i], buttons[j]) > 4 then
			table.insert(overlaps, buttons[i].name .. " <-> " .. buttons[j].name)
		end
	end
end
local highlights = 0
for _, inst in game:GetDescendants() do
	if inst:IsA("Highlight") then
		highlights += 1
	end
end
return {
	visibleButtons = #buttons,
	smallTouchTargets = small,
	buttonOverlaps = overlaps,
	jumpButton = if jumpBox then jumpBox.name else nil,
	jumpOverlaps = jumpHits,
	inputSwallowingFrames = swallowing,
	clientHighlightsIncludingDisabled = highlights,
}
```

---

## 2. Traversal Snag, Step-Riser & Camera Occlusion Probe (`datamodel_type: "Client"`)

Hold movement through the suspect area throughout the two-second sample. The probe excludes the first 0.2 seconds of each continuous input, reports the longest low-speed interval and its position, and marks insufficient sustained input inconclusive. Verify potential snags, step hazards and camera occlusion in play; speed alone is not proof of a collision.

```lua
--!strict
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")

local player = Players.LocalPlayer
assert(player, "LocalPlayer missing")
local character = player.Character
assert(character, "Character not spawned")
local humanoid = character:FindFirstChildOfClass("Humanoid")
local rootPart = character:FindFirstChild("HumanoidRootPart") :: BasePart?
assert(humanoid and rootPart, "Humanoid or HumanoidRootPart missing")

local camera = workspace.CurrentCamera
local rayParams = RaycastParams.new()
rayParams.FilterType = Enum.RaycastFilterType.Exclude
rayParams.FilterDescendantsInstances = { character }

-- 1. Check ankle-level step or prop obstructions along current facing/move direction
local lookDir = if humanoid.MoveDirection.Magnitude > 0.05
	then humanoid.MoveDirection.Unit
	else rootPart.CFrame.LookVector
local ankleOrigin = rootPart.Position - Vector3.new(0, rootPart.Size.Y * 0.45, 0)
local kneeOrigin = rootPart.Position + Vector3.new(0, 0.4, 0)

local ankleHit = workspace:Raycast(ankleOrigin, lookDir * 4.5, rayParams)
local kneeHit = workspace:Raycast(kneeOrigin, lookDir * 4.5, rayParams)

local stepHazard: string? = nil
if ankleHit and ankleHit.Instance and ankleHit.Instance.CanCollide and ankleHit.Normal.Y < 0.5 then
	local part = ankleHit.Instance
	local partTopY = (part.CFrame * CFrame.new(0, part.Size.Y * 0.5, 0)).Y
	local footBottomY = rootPart.Position.Y - (rootPart.Size.Y * 0.5) - humanoid.HipHeight
	local stepRiser = partTopY - footBottomY
	if not kneeHit and stepRiser > 0.4 and stepRiser < 2.2 then
		stepHazard = string.format(
			"%s (step riser %.2f studs > 0.40 stud smooth threshold)",
			part:GetFullName(),
			stepRiser
		)
	end
end

-- 2. Check camera line-of-sight for decorative parts with CanCollide=false but CanQuery=true
local cameraPopcluders: { string } = {}
if camera then
	local camVec = camera.CFrame.Position - rootPart.Position
	local camHit = workspace:Raycast(rootPart.Position, camVec, rayParams)
	if camHit and camHit.Instance then
		local hitPart = camHit.Instance
		if not hitPart.CanCollide and hitPart.CanQuery then
			table.insert(
				cameraPopcluders,
				hitPart:GetFullName() .. " (CanCollide=false but CanQuery=true)"
			)
		end
	end
end

local start = os.clock()
local held, longestHeld, sampled, blocked, longest = 0, 0, 0, 0, 0
local worstPosition: Vector3? = nil
while os.clock() - start < 2 do
	local dt = math.min(RunService.Heartbeat:Wait(), 0.1)
	if humanoid.MoveDirection.Magnitude > 0.5 then
		held += dt
		longestHeld = math.max(longestHeld, held)
		if held > 0.2 then
			sampled += dt
			local velocity = rootPart.AssemblyLinearVelocity
			local speed = Vector3.new(velocity.X, 0, velocity.Z).Magnitude
			if speed < 1.2 then
				blocked += dt
				if blocked > longest then
					longest = blocked
					worstPosition = rootPart.Position
				end
			else
				blocked = 0
			end
		end
	else
		held, blocked = 0, 0
	end
end
return {
	status = if longestHeld < 0.7 then "inconclusive: insufficient sustained input" else "sampled",
	sampledSeconds = sampled,
	longestLowSpeedSeconds = longest,
	worstPosition = worstPosition,
	stepHazard = stepHazard,
	cameraHeightAboveRoot = if camera then camera.CFrame.Position.Y - rootPart.Position.Y else nil,
	cameraPopcluders = cameraPopcluders,
}
```

---

## 3. Control Ergonomics, Modal Priority & Prompt Parity Probe (`datamodel_type: "Client"`)

Inspects bound actions in `ContextActionService`, checks whether visible HUD/tutorial prompts match the active `UserInputService.PreferredInput`, and checks whether open modals set `GuiService.SelectedObject` for gamepad navigation.

```lua
--!strict
local ContextActionService = game:GetService("ContextActionService")
local GuiService = game:GetService("GuiService")
local Players = game:GetService("Players")
local UserInputService = game:GetService("UserInputService")

local player = Players.LocalPlayer
assert(player, "LocalPlayer missing")
local playerGui = player:WaitForChild("PlayerGui") :: PlayerGui

local preferredInput = tostring(UserInputService.PreferredInput)
local boundActions = ContextActionService:GetAllBoundActionInfo()
local actionSummary: { { name: string, priority: number, inputTypes: { string } } } = {}

for actionName, info in boundActions do
	local types: { string } = {}
	if type(info.inputTypes) == "table" then
		for _, t in info.inputTypes do
			table.insert(types, tostring(t))
		end
	end
	table.insert(actionSummary, {
		name = tostring(actionName),
		priority = tonumber(info.priorityLevel) or 0,
		inputTypes = types,
	})
end

local function isEffectivelyVisible(gui: GuiObject): boolean
	if not gui.Visible then
		return false
	end
	local current: Instance? = gui.Parent
	while current and current ~= playerGui do
		if current:IsA("GuiObject") and not current.Visible then
			return false
		end
		if current:IsA("LayerCollector") and not current.Enabled then
			return false
		end
		current = current.Parent
	end
	return true
end

local keyboardLeakLabels: { string } = {}
for _, inst in playerGui:GetDescendants() do
	if (inst:IsA("TextLabel") or inst:IsA("TextButton")) and isEffectivelyVisible(inst) then
		local text = inst.Text
		if preferredInput ~= "Enum.PreferredInput.KeyboardAndMouse" then
			if
				string.find(text, "%[E%]")
				or string.find(text, "%[H%]")
				or string.find(text, "%[Q%]")
				or string.find(text, "%[F%]")
				or string.find(text, "Press Space")
			then
				table.insert(keyboardLeakLabels, inst:GetFullName() .. ": " .. text)
			end
		end
	end
end

return {
	preferredInput = preferredInput,
	autoSelectGuiEnabled = GuiService.AutoSelectGuiEnabled,
	guiNavigationEnabled = GuiService.GuiNavigationEnabled,
	selectedObject = if GuiService.SelectedObject
		then GuiService.SelectedObject:GetFullName()
		else nil,
	boundActionCount = #actionSummary,
	boundActions = actionSummary,
	keyboardPromptLeaksOnNonKeyboard = keyboardLeakLabels,
}
```

---

## 4. Server Authority & Pacing Probe (`datamodel_type: "Server"`)

Audits server-side game state, player attributes (`InLobby`, suit equip, charge, carried objectives), and decorative micro-part collision hygiene.

```lua
--!strict
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local playerSnapshots: { { [string]: any } } = {}
for _, p in Players:GetPlayers() do
	table.insert(playerSnapshots, {
		name = p.Name,
		attributes = p:GetAttributes(),
	})
end

local collidableTinyParts: { string } = {}
for _, inst in workspace:GetDescendants() do
	if inst:IsA("BasePart") then
		if inst.CanCollide and inst.Transparency < 1 and inst.Size.Magnitude < 0.65 then
			if #collidableTinyParts < 20 then
				table.insert(collidableTinyParts, inst:GetFullName())
			end
		end
	end
end

return {
	workspaceAttributes = workspace:GetAttributes(),
	replicatedAttributes = ReplicatedStorage:GetAttributes(),
	players = playerSnapshots,
	collidableTinyParts = collidableTinyParts,
}
```

---

## 5. Studio Script Inventory & Drift Probe (`datamodel_type: "Edit"`)

Enumerate every Studio `LuaSourceContainer`, including its exact source or read error. Using the project mapping, compare each mapped disk script's exact source to Studio, accounting for configured transforms. Check both directions for missing, extra, duplicated or ambiguous mappings. Matching lengths or line counts are not parity. A missing mapping, unreadable source, truncated output or unresolved discrepancy is inconclusive, never PASS; read affected scripts individually if needed.

```lua
--!strict
type ScriptEntry = { path: string, className: string, source: string?, error: string? }
local inventory: { ScriptEntry } = {}
for _, inst in game:GetDescendants() do
	if inst:IsA("LuaSourceContainer") then
		local ok, result = pcall(function()
			return (inst :: any).Source :: string
		end)
		table.insert(inventory, {
			path = inst:GetFullName(),
			className = inst.ClassName,
			source = if ok then result else nil,
			error = if ok then nil else tostring(result),
		})
	end
end
table.sort(inventory, function(a: ScriptEntry, b: ScriptEntry): boolean
	return a.path < b.path
end)
return { totalScripts = #inventory, scripts = inventory }
```
