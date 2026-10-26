# Live Studio Playtest Probes (`execute_luau`)

Use these self-contained `--!strict` Luau snippets with the `Roblox_Studio` MCP `execute_luau` tool during autonomous playtest runs. Every probe cleans up any temporary instances before returning a structured table.

---

## 1. UI, CoreGui & Mobile Thumbzone Collision Probe (`datamodel_type: "Client"`)

Detects undersized touch targets (`< 48x48` px), button-on-button overlaps, collisions with Roblox's top-right `PlayerList`, topbar inset, or bottom-right mobile Jump zone, and large `Active = true` containers that accidentally swallow camera drag.

```lua
--!strict
local GuiService = game:GetService("GuiService")
local Players = game:GetService("Players")
local StarterGui = game:GetService("StarterGui")

local player = Players.LocalPlayer
assert(player, "LocalPlayer missing; run in Client datamodel_type during Play mode")
local playerGui = player:WaitForChild("PlayerGui") :: PlayerGui
local camera = workspace.CurrentCamera
local viewport = if camera then camera.ViewportSize else Vector2.new(1920, 1080)
local topLeftInset, _bottomRightInset = GuiService:GetGuiInset()

local playerListEnabled = true
pcall(function()
	playerListEnabled = StarterGui:GetCoreGuiEnabled(Enum.CoreGuiType.PlayerList)
end)

type BoxInfo = { name: string, pos: Vector2, size: Vector2 }
local visibleButtons: { BoxInfo } = {}
local smallTouchTargets: { string } = {}
local buttonOverlaps: { string } = {}
local coreGuiCollisions: { string } = {}
local inputSwallowingFrames: { string } = {}

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

local function rectIntersectionArea(
	aPos: Vector2,
	aSize: Vector2,
	bPos: Vector2,
	bSize: Vector2
): number
	local ix = math.max(0, math.min(aPos.X + aSize.X, bPos.X + bSize.X) - math.max(aPos.X, bPos.X))
	local iy = math.max(0, math.min(aPos.Y + aSize.Y, bPos.Y + bSize.Y) - math.max(aPos.Y, bPos.Y))
	return ix * iy
end

local topRightPlayerListPos = Vector2.new(math.max(0, viewport.X - 180), 0)
local topRightPlayerListSize = Vector2.new(180, 220)
local mobileJumpPos = Vector2.new(math.max(0, viewport.X - 140), math.max(0, viewport.Y - 140))
local mobileJumpSize = Vector2.new(140, 140)
local viewportArea = math.max(1, viewport.X * viewport.Y)

for _, inst in playerGui:GetDescendants() do
	if inst:IsA("GuiObject") and isEffectivelyVisible(inst) then
		local pos = inst.AbsolutePosition
		local size = inst.AbsoluteSize
		if inst:IsA("GuiButton") and inst.Active then
			if size.X < 48 or size.Y < 48 then
				table.insert(
					smallTouchTargets,
					string.format(
						"%s (%dx%d px)",
						inst:GetFullName(),
						math.floor(size.X),
						math.floor(size.Y)
					)
				)
			end
			if pos.Y < topLeftInset.Y and pos.X < 160 then
				table.insert(coreGuiCollisions, inst:GetFullName() .. " overlaps TopBar inset")
			end
			if
				playerListEnabled
				and rectIntersectionArea(
						pos,
						size,
						topRightPlayerListPos,
						topRightPlayerListSize
					)
					> 16
			then
				table.insert(
					coreGuiCollisions,
					inst:GetFullName() .. " overlaps top-right PlayerList"
				)
			end
			if rectIntersectionArea(pos, size, mobileJumpPos, mobileJumpSize) > 16 then
				table.insert(
					coreGuiCollisions,
					inst:GetFullName() .. " overlaps bottom-right TouchGui Jump"
				)
			end
			table.insert(visibleButtons, { name = inst:GetFullName(), pos = pos, size = size })
		elseif not inst:IsA("GuiButton") and inst.Active then
			local areaRatio = (size.X * size.Y) / viewportArea
			if areaRatio > 0.25 and inst.BackgroundTransparency > 0.9 then
				table.insert(
					inputSwallowingFrames,
					string.format(
						"%s (Active=true covering %.0f%% of screen)",
						inst:GetFullName(),
						areaRatio * 100
					)
				)
			end
		end
	end
end

for i = 1, #visibleButtons do
	for j = i + 1, #visibleButtons do
		local a = visibleButtons[i]
		local b = visibleButtons[j]
		local area = rectIntersectionArea(a.pos, a.size, b.pos, b.size)
		if area > 4 then
			table.insert(
				buttonOverlaps,
				string.format("%s <-> %s (%.0f sq px)", a.name, b.name, area)
			)
		end
	end
end

return {
	viewport = { x = viewport.X, y = viewport.Y },
	visibleButtons = #visibleButtons,
	smallTouchTargets = smallTouchTargets,
	buttonOverlaps = buttonOverlaps,
	coreGuiCollisions = coreGuiCollisions,
	inputSwallowingFrames = inputSwallowingFrames,
}
```

---

## 2. Traversal Snag, Step-Riser & Camera Occlusion Probe (`datamodel_type: "Client"`)

Run while or immediately after moving the character through doorways, porch steps, bridges, or forest lanes. Detects ankle-height collision snags, uncollidable visual props that still block camera raycasts (`CanQuery == true`), and low camera framing on small rigs.

```lua
--!strict
local Players = game:GetService("Players")

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

local horizVel =
	Vector3.new(rootPart.AssemblyLinearVelocity.X, 0, rootPart.AssemblyLinearVelocity.Z).Magnitude
local isSnagged = humanoid.MoveDirection.Magnitude > 0.5 and horizVel < 1.2

return {
	position = { x = rootPart.Position.X, y = rootPart.Position.Y, z = rootPart.Position.Z },
	moveDirectionMagnitude = humanoid.MoveDirection.Magnitude,
	horizontalSpeed = horizVel,
	verticalSpeed = rootPart.AssemblyLinearVelocity.Y,
	floorMaterial = tostring(humanoid.FloorMaterial),
	isSnagged = isSnagged,
	stepHazard = stepHazard,
	cameraOffset = {
		x = humanoid.CameraOffset.X,
		y = humanoid.CameraOffset.Y,
		z = humanoid.CameraOffset.Z,
	},
	cameraHeightAboveRoot = if camera then camera.CFrame.Position.Y - rootPart.Position.Y else 0,
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

## 4. Server Authority, Pacing & Highlight Budget Probe (`datamodel_type: "Server"`)

Audits server-side game state, player attributes (`InLobby`, suit equip, charge, carried objectives), active `Highlight` count against Roblox's 31-instance limit, and decorative micro-part collision hygiene.

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

local activeHighlights = 0
local collidableTinyParts: { string } = {}
for _, inst in workspace:GetDescendants() do
	if inst:IsA("Highlight") and inst.Enabled then
		activeHighlights += 1
	elseif inst:IsA("BasePart") then
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
	activeHighlights = activeHighlights,
	highlightBudgetOk = activeHighlights <= 31,
	collidableTinyParts = collidableTinyParts,
}
```

---

## 5. Studio Script Inventory & Drift Probe (`datamodel_type: "Edit"`)

Summarizes all `LuaSourceContainer` scripts under `ReplicatedStorage.Shared`, `ServerScriptService.Server`, and `StarterPlayer.StarterPlayerScripts.Client` with byte lengths and line counts so the agent can verify zero drift between disk source and Studio `Edit` mode before and after long fix runs.

```lua
--!strict
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local ServerScriptService = game:GetService("ServerScriptService")
local StarterPlayer = game:GetService("StarterPlayer")

local roots: { Instance } = {}
local sharedRoot = ReplicatedStorage:FindFirstChild("Shared")
local serverRoot = ServerScriptService:FindFirstChild("Server")
local starterScripts = StarterPlayer:FindFirstChild("StarterPlayerScripts")
local clientRoot = if starterScripts then starterScripts:FindFirstChild("Client") else nil

if sharedRoot then
	table.insert(roots, sharedRoot)
end
if serverRoot then
	table.insert(roots, serverRoot)
end
if clientRoot then
	table.insert(roots, clientRoot)
end

type ScriptMeta = { path: string, className: string, bytes: number, lines: number }
local inventory: { ScriptMeta } = {}

for _, root in roots do
	local list = root:GetDescendants()
	table.insert(list, 1, root)
	for _, inst in list do
		if inst:IsA("LuaSourceContainer") then
			local src = (inst :: any).Source :: string
			local _, newlines = string.gsub(src, "\n", "\n")
			table.insert(inventory, {
				path = inst:GetFullName(),
				className = inst.ClassName,
				bytes = #src,
				lines = newlines + 1,
			})
		end
	end
end

table.sort(inventory, function(a: ScriptMeta, b: ScriptMeta): boolean
	return a.path < b.path
end)

return {
	totalScripts = #inventory,
	scripts = inventory,
}
```

