-- name: [CS] Kid Goku
-- description: Kid Goku from the original Dragon Ball, in his Pilaf-saga gi.\n\nB: Jan Ken combo, hold for the Kamehameha\nY: Flying Nimbus\n\nHis voice is Japanese, or English in this mod's menu.\n\n\\#ff7777\\Requires Character Select.

local TEXT_MOD_NAME = get_active_mod().name

if not _G.charSelectExists then
    djui_popup_create("\\#ffffdc\\\n" .. TEXT_MOD_NAME .. "\nneeds the Character Select mod.\nTurn it on and restart the room.", 6)
    return 0
end

local TEX_GOKU_ICON = get_texture_info("goku_icon")

local VOICE_GOKU = {
    [CHAR_SOUND_OKEY_DOKEY] = "goku_start.ogg",
    [CHAR_SOUND_LETS_A_GO] = "goku_lets_go.ogg",
    [CHAR_SOUND_GAME_OVER] = "goku_game_over.ogg",
    [CHAR_SOUND_PUNCH_YAH] = "goku_rock.ogg",
    [CHAR_SOUND_PUNCH_WAH] = "goku_scissors.ogg",
    [CHAR_SOUND_PUNCH_HOO] = "goku_paper.ogg",
    [CHAR_SOUND_YAH_WAH_HOO] = {"goku_jump1.ogg", "goku_jump2.ogg", "goku_jump3.ogg"},
    [CHAR_SOUND_HOOHOO] = "goku_double_jump.ogg",
    [CHAR_SOUND_YAHOO_WAHA_YIPPEE] = {"goku_triple_jump1.ogg", "goku_triple_jump2.ogg"},
    [CHAR_SOUND_YAHOO] = "goku_long_jump.ogg",
    [CHAR_SOUND_UH] = "goku_bonk.ogg",
    [CHAR_SOUND_UH2] = "goku_ledge.ogg",
    [CHAR_SOUND_UH2_2] = "goku_land.ogg",
    [CHAR_SOUND_DOH] = "goku_bonk.ogg",
    [CHAR_SOUND_OOOF] = "goku_hurt.ogg",
    [CHAR_SOUND_OOOF2] = "goku_hurt.ogg",
    [CHAR_SOUND_HAHA] = "goku_land.ogg",
    [CHAR_SOUND_HAHA_2] = "goku_land.ogg",
    [CHAR_SOUND_WHOA] = "goku_ledge.ogg",
    [CHAR_SOUND_EEUH] = "goku_ledge.ogg",
    [CHAR_SOUND_WAAAOOOW] = "goku_falling.ogg",
    [CHAR_SOUND_TWIRL_BOUNCE] = "goku_double_jump.ogg",
    [CHAR_SOUND_GROUND_POUND_WAH] = "goku_shout_haa.ogg",
    [CHAR_SOUND_WAH2] = "goku_throw.ogg",
    [CHAR_SOUND_HRMM] = "goku_lift.ogg",
    [CHAR_SOUND_HERE_WE_GO] = "goku_yatta.ogg",
    [CHAR_SOUND_SO_LONGA_BOWSER] = "goku_throw.ogg",
    [CHAR_SOUND_ATTACKED] = "goku_hurt.ogg",
    [CHAR_SOUND_PANTING] = "goku_panting.ogg",
    [CHAR_SOUND_PANTING_COLD] = "goku_panting.ogg",
    [CHAR_SOUND_ON_FIRE] = "goku_burned.ogg",
    [CHAR_SOUND_IMA_TIRED] = "goku_tired.ogg",
    [CHAR_SOUND_YAWNING] = "goku_tired.ogg",
    [CHAR_SOUND_DYING] = "goku_dying.ogg",
    [CHAR_SOUND_DROWNING] = "goku_dying.ogg",
    [CHAR_SOUND_MAMA_MIA] = "goku_hurt.ogg",
}

local function loaded_voice(english)
    local function load(file)
        local twin = goku_english_of(file)
        if english and mod_file_exists("sound/" .. twin) then return audio_sample_load(twin) end
        return mod_file_exists("sound/" .. file) and audio_sample_load(file) or nil
    end
    local out = {}
    for k, v in pairs(VOICE_GOKU) do
        if type(v) == "table" then
            local list = {}
            for _, f in ipairs(v) do list[#list + 1] = load(f) end
            if #list > 0 then out[k] = list end
        else
            out[k] = load(v)
        end
    end
    return out
end

local voices = {}
local function set_english(on)
    gGokuEnglish = on
    _G.charSelect.character_add_voice(E_MODEL_GOKU, voices[on])
end

local OWN_ACTIONS = {[ACT_GOKU_KAME] = true, [ACT_GOKU_NIMBUS_CALL] = true, [ACT_GOKU_NIMBUS] = true}

local function goku_update(m)
    local g = gGoku[m.playerIndex]
    if not OWN_ACTIONS[m.action] and (g.stompLeft or 0) <= 0 then g.anim = nil end

    goku_face_update(m)

    if m.freeze > 0 then return end
    goku_kame_update(m)
    goku_nimbus_update(m)
end

local function on_character_select_load()
    goku_load_sounds()
    goku_load_song()
    CT_GOKU = _G.charSelect.character_add("Kid Goku",
        "The boy with a tail from Mount Paozu, trained by Master Roshi. Jan Ken, Kamehameha, Nimbus.",
        "Metal Fox", "4E5CC4", E_MODEL_GOKU, CT_MARIO, TEX_GOKU_ICON, 1)
    voices = {[false] = loaded_voice(false), [true] = loaded_voice(true)}
    set_english(gGokuEnglish)
    _G.charSelect.character_add_animations(E_MODEL_GOKU, GOKU_CHAR_ANIMS, nil, GOKU_CHAR_HANDS)

    _G.charSelect.character_add_caps(E_MODEL_GOKU, {wing = E_MODEL_GOKU_DRAGON_BALL, metalWing = E_MODEL_GOKU_DRAGON_BALL})
    _G.charSelect.character_hook_moveset(CT_GOKU, HOOK_MARIO_UPDATE, goku_update)
    _G.charSelect.character_hook_moveset(CT_GOKU, HOOK_BEFORE_PHYS_STEP, goku_before_phys_step)
    _G.charSelect.character_hook_moveset(CT_GOKU, HOOK_ON_SET_MARIO_ACTION, goku_on_set_action)
    _G.charSelect.character_set_category(CT_GOKU, "Dragon Ball")
    _G.charSelect.credit_add(TEXT_MOD_NAME, "Metal Fox", "Kid Goku")
end

hook_event(HOOK_ON_MODS_LOADED, on_character_select_load)

hook_mod_menu_checkbox("English Voice", gGokuEnglish, function(_, on)
    mod_storage_save_bool("englishVoice", on)
    set_english(on)
end)

_G.kidGoku = {
    actions = {kame = ACT_GOKU_KAME, nimbusCall = ACT_GOKU_NIMBUS_CALL, nimbus = ACT_GOKU_NIMBUS},
    behaviors = {beam = id_bhvGokuBeam, ball = id_bhvGokuBall, dash = id_bhvGokuDash, burst = id_bhvGokuBurst,
        spark = id_bhvGokuSpark, nimbus = id_bhvGokuNimbus, trail = id_bhvGokuTrail, tail = id_bhvGokuTail, carried = id_bhvGokuCarried},
    dragonBall = E_MODEL_GOKU_DRAGON_BALL,
    model = E_MODEL_GOKU,
    beamLength = function(i)
        local m = gMarioStates[i]
        return m.action == ACT_GOKU_KAME and m.actionState == 1 and goku_alive(gGoku[i].beam) and gGoku[i].beamLength or 0
    end,
    character = function() return CT_GOKU end,
    tail = function(i) return gGoku[i].tail end,
    bodyYaw = goku_body_yaw,
    lastSound = function(i) return gGoku[i].lastSound end,
    played = function(i, file) return (gGoku[i].played or {})[file] or 0 end,
    setEnglish = set_english,
    faces = GOKU_FACES,
    stompLeft = function(i) return gGoku[i].stompLeft or 0 end,
    blending = function(i) return goku_blending(i) end,

    wingSong = function() return gGoku[0].songOn == true, gGoku[0].songSwapped == true end,
}
