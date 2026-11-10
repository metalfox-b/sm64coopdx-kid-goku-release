-- name: Kid Goku two-player check
-- description: Two Kid Gokus in one room; the client charges and fires while the host watches, misses with a punch, lands one on a

local tick, chose, sawCharge, sawWave, sawCleanup, sawImpact, hostDone = 0, false, false, false, false, false, nil
local stompSound, stompClip, sawRemoteStomp = nil, nil, false
local fellOnNothing = nil

hook_event(HOOK_BEFORE_MARIO_UPDATE, function(m)
    if m.playerIndex == 0 and _G.kidGoku and _G.kidGoku.stompLeft(0) > 0 and not stompClip then
        stompClip = smlua_anim_util_get_current_animation_name(m.marioObj)
    end
end)
local function say(x) print("[PAIR] " .. x) end

hook_event(HOOK_BEFORE_MARIO_UPDATE, function(m)
    if m.playerIndex ~= 0 then return end
    if get_dialog_id() >= 0 then
        m.controller.buttonDown, m.controller.buttonPressed = A_BUTTON, A_BUTTON
        return
    end
    if network_is_server() or tick < 200 then return end
    local c = m.controller
    c.buttonDown = (tick >= 300 and tick < 392) and B_BUTTON or 0
    c.buttonPressed = (tick == 300 or tick == 485 or tick == 530) and B_BUTTON or 0

    if tick == 720 or tick == 1330 or tick == 1420 or tick == 1560 then
        c.buttonDown, c.buttonPressed = c.buttonDown | Y_BUTTON, c.buttonPressed | Y_BUTTON
    end
end)

local function tail_gap(api, i)
    local link = api.tail(i)
    if not link then return nil end
    local m = gMarioStates[i]
    local dx, dz = link.header.gfx.pos.x - m.pos.x, link.header.gfx.pos.z - m.pos.z
    return math.sqrt(dx * dx + dz * dz)
end

local ride = {phase = "wait", base = 0}
local function clouds(api)
    local n, o = 0, obj_get_first_with_behavior_id(api.behaviors.nimbus)
    while o do
        if o.oAction < 3 then n = n + 1 end
        o = obj_get_next_with_same_behavior_id(o)
    end
    return n
end
local function watch_nimbus(api, remote)
    local r = ride
    local riding, calling = remote.action == api.actions.nimbus, remote.action == api.actions.nimbusCall
    local shouts = api.played(1, "goku_lets_go.ogg") - r.base
    if r.phase == "wait" then
        if calling or riding then
            r.phase, r.most, r.least, r.frames = "first", 0, 99, 0
        else
            r.base = api.played(1, "goku_lets_go.ogg")
        end
    elseif r.phase == "first" and riding then
        r.frames = r.frames + 1
        local n = clouds(api)
        r.most, r.least = math.max(r.most, n), math.min(r.least, n)
        if r.frames == 60 then
            say(string.format("remote rides one cloud %s (%d to %d)", tostring(r.most == 1 and r.least == 1), r.least, r.most))
            say(string.format("remote called once %s (%d)", tostring(shouts == 1), shouts))

            set_mario_action(remote, ACT_IDLE, 0)
            r.phase, r.at = "landed", tick
        end
    elseif r.phase == "landed" and tick >= r.at + 60 then
        say(string.format("remote keeps a cloud after a false landing %s (%d clouds, %d calls, action 0x%x)",
            tostring(riding and clouds(api) == 1 and shouts == 1), clouds(api), shouts, remote.action))
        warp_to_level(LEVEL_CASTLE_GROUNDS, 1, 1)
        r.phase, r.at = "away", tick
    elseif r.phase == "away" and tick >= r.at + 90 then
        warp_to_level(LEVEL_BOB, 1, 1)
        r.phase, r.at = "back", tick
    elseif r.phase == "back" and tick >= r.at + 200 then
        say(string.format("remote has a cloud when first seen riding %s (%d clouds, action 0x%x)",
            tostring(riding and clouds(api) == 1), clouds(api), remote.action))
        r.phase = "second"
    elseif r.phase == "second" and calling and remote.actionTimer >= 5 then

        set_mario_action(remote, api.actions.nimbus, 0)
        r.phase, r.at = "early", tick
    elseif r.phase == "early" and tick >= r.at + 70 then
        say(string.format("remote calls once after an early end %s (%d calls, %d clouds, action 0x%x)",
            tostring(riding and shouts == 2 and clouds(api) == 1), shouts, clouds(api), remote.action))
        r.phase = "done"
        hostDone = tick + 30
    end
end

hook_event(HOOK_MARIO_UPDATE, function(m)
    if m.playerIndex ~= 0 or not _G.kidGoku or not gNetworkPlayers[1].connected then return end
    local api = _G.kidGoku
    if tick == 5 then warp_to_level(LEVEL_BOB, 1, 1) end
    if tick > 205 and not chose then
        _G.charSelect.character_set_current_number(api.character(), 1)
        _G.charSelect.set_menu_open(false)
        chose = true
    end
    if tick == 280 then

        m.pos.x = m.pos.x + (network_is_server() and 300 or -300)
        set_mario_action(m, ACT_IDLE, 0)
    end
    if tick == 296 then
        local mine, theirs = tail_gap(api, 0), tail_gap(api, 1)
        say(string.format("tails own %s other %s", tostring(mine), tostring(theirs)))
        say("tails on their players " .. tostring(mine ~= nil and theirs ~= nil and mine < 40 and theirs < 40))
    end
    if network_is_server() then
        local remote = gMarioStates[1]
        if remote.action == api.actions.kame and remote.actionState == 0 and not sawCharge
            and obj_get_first_with_behavior_id(api.behaviors.ball) then
            sawCharge = true
            say("remote charge")
        end
        if api.beamLength(1) > 150 and not sawWave then
            sawWave = true
            say("remote beam")
        end
        local leftover = false
        for _, b in ipairs({api.behaviors.beam, api.behaviors.ball, api.behaviors.dash, api.behaviors.burst}) do
            leftover = leftover or obj_get_first_with_behavior_id(b) ~= nil
        end
        if sawWave and remote.action ~= api.actions.kame and not leftover and not sawCleanup then
            sawCleanup = true
            say("remote cleanup")
        end
        if api.lastSound(1) == "goku_punch.ogg" and not sawImpact then
            sawImpact = true
            say("remote impact")
        end
        if api.stompLeft(1) > 0 and not sawRemoteStomp then
            sawRemoteStomp = true
            say("remote stomp")
        end
        watch_nimbus(api, remote)
        if tick == hostDone then say("host done") end
    else
        if tick == 365 then say("client charge " .. tostring(m.action == api.actions.kame and m.actionState == 0)) end
        if tick == 406 then say("client beam " .. tostring(api.beamLength(0) > 150)) end
        if tick == 484 then set_mario_action(m, ACT_IDLE, 0) end
        if tick == 515 then
            say("client miss " .. tostring(api.lastSound(0) == "goku_swing.ogg"))
            set_mario_action(m, ACT_IDLE, 0)
        end
        if tick == 525 then
            local yaw = m.faceAngle.y
            spawn_non_sync_object(id_bhvGoomba, E_MODEL_GOOMBA, m.pos.x + sins(yaw) * 140, m.pos.y, m.pos.z + coss(yaw) * 140, nil)
        end
        if tick == 560 then
            say("client impact " .. tostring(api.lastSound(0) == "goku_punch.ogg"))
            set_mario_action(m, ACT_IDLE, 0)
        end
        if tick == 575 then
            spawn_non_sync_object(id_bhvGoomba, E_MODEL_GOOMBA, m.pos.x, m.pos.y, m.pos.z, nil)
            m.pos.y = m.pos.y + 220
            m.vel.y = 0
            set_mario_action(m, ACT_FREEFALL, 0)
        end
        if api.stompLeft(0) > 0 and not stompSound then stompSound = api.lastSound(0) end
        if tick == 620 then
            say("client stomp " .. tostring(stompSound == "goku_heavy_kick.ogg") .. " " .. tostring(stompSound))
            say("client stomp clip " .. tostring(stompClip == "goku_stomp_enemy") .. " " .. tostring(stompClip))
            set_mario_action(m, ACT_IDLE, 0)
        end
        if tick == 640 then
            stompClip = nil
            m.pos.y = m.pos.y + 220
            m.vel.y = 0
            set_mario_action(m, ACT_FREEFALL, 0)
        end
        if tick > 640 and tick < 700 and api.stompLeft(0) > 0 then fellOnNothing = true end
        if tick == 700 then
            say("client no stomp without an enemy " .. tostring(not fellOnNothing))
            set_mario_action(m, ACT_IDLE, 0)
        end
        if tick == 800 then say("client rides the Nimbus " .. tostring(m.action == api.actions.nimbus)) end
        if tick == 1400 then
            m.pos.y = m.floorHeight
            set_mario_action(m, ACT_IDLE, 0)
        end
        if tick == 1500 then say("client rides it again " .. tostring(m.action == api.actions.nimbus)) end
        if tick == 1620 then say("client done") end
    end
    tick = tick + 1
end)
