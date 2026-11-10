if not _G.charSelectExists then return end

define_custom_obj_fields({oGokuOwner = 's32', oGokuTag = 's32', oGokuHitTag = 's32', oGokuCharge = 'f32',
    oGokuLength = 'f32'})

E_MODEL_GOKU = smlua_model_util_get_id("goku_geo")

E_MODEL_GOKU_BEAM = smlua_model_util_get_id("goku_beam_geo")
E_MODEL_GOKU_BALL = smlua_model_util_get_id("goku_ball_geo")
E_MODEL_GOKU_DASH = smlua_model_util_get_id("goku_dash_geo")
E_MODEL_GOKU_BURST = smlua_model_util_get_id("goku_burst_geo")
E_MODEL_GOKU_NIMBUS = smlua_model_util_get_id("goku_nimbus_geo")
E_MODEL_GOKU_TRAIL = smlua_model_util_get_id("goku_trail_geo")
E_MODEL_GOKU_TAIL = smlua_model_util_get_id("goku_tail_geo")
E_MODEL_GOKU_DRAGON_BALL = smlua_model_util_get_id("goku_dragon_ball_geo")

gGoku = {}
for i = 0, MAX_PLAYERS - 1 do
    gGoku[i] = {bHeld = 0, faceHold = 0, beam = nil, ball = nil, nimbus = nil, tail = nil, tagSeen = {}}
end

local nextTag = 0
function goku_new_tag()
    nextTag = nextTag + 1
    return nextTag
end

GOKU_ANIMS = GOKU_ANIMS or {}
function goku_anim(m, name)
    local g = gGoku[m.playerIndex]
    if g.anim ~= name then
        g.anim = name
        set_character_animation(m, CHAR_ANIM_A_POSE)
        set_anim_to_frame(m, 0)
    end
    smlua_anim_util_set_animation(m.marioObj, name)
end

gGokuEnglish = mod_storage_load_bool("englishVoice", false)

function goku_english_of(file)
    return (file:gsub("^goku_", "goku_en_"))
end

local samples = {}
function goku_load_sounds()
    for _, file in ipairs({"goku_ka.ogg", "goku_me.ogg", "goku_ha2.ogg", "goku_me2.ogg", "goku_ha.ogg",
            "goku_kame_rise1.ogg", "goku_kame_rise2.ogg", "goku_kame_rise3.ogg", "goku_kame_rise4.ogg", "goku_kame_rise5.ogg",
            "goku_kame_rise6.ogg", "goku_kame_fire.ogg", "goku_kame_fire_short.ogg", "goku_kame_impact.ogg", "goku_lets_go.ogg", "goku_punch.ogg", "goku_heavy_punch.ogg", "goku_heavy_kick.ogg", "goku_leap.ogg",
            "goku_leap_big.ogg", "goku_land_tap.ogg", "goku_throw.ogg", "goku_swing.ogg", "goku_swing_big.ogg", "goku_shout_ha.ogg",
            "goku_shout_ha2.ogg", "goku_shout_ya.ogg", "goku_shout_arya.ogg", "goku_shout_orya.ogg", "goku_shout_aryaa.ogg",
            "goku_shout_haa.ogg", "goku_yatta.ogg", "goku_nimbus.ogg"}) do
        if mod_file_exists("sound/" .. file) then samples[file] = audio_sample_load(file) end
        local english = goku_english_of(file)
        if mod_file_exists("sound/" .. english) then samples[english] = audio_sample_load(english) end
    end
end

function goku_sound(m, file, volume, position)
    local english = goku_english_of(file)
    local said = gGokuEnglish and samples[english] and english or file
    gGoku[m.playerIndex].lastSound = said
    local played = gGoku[m.playerIndex].played or {}
    played[said] = (played[said] or 0) + 1
    gGoku[m.playerIndex].played = played
    if samples[said] then audio_sample_play(samples[said], position or m.pos, volume or 1) end
end

function goku_hands(m, ahead, up)
    local yaw = m.faceAngle.y
    return m.pos.x + sins(yaw) * ahead, m.pos.y + up, m.pos.z + coss(yaw) * ahead
end

local function seg_dist(px, py, pz, ax, ay, az, bx, by, bz)
    local dx, dy, dz = bx - ax, by - ay, bz - az
    local len2 = dx * dx + dy * dy + dz * dz
    local t = len2 > 0 and math.max(0, math.min(1, ((px - ax) * dx + (py - ay) * dy + (pz - az) * dz) / len2)) or 0
    local cx, cy, cz = ax + dx * t - px, ay + dy * t - py, az + dz * t - pz
    return math.sqrt(cx * cx + cy * cy + cz * cz)
end

function goku_ray_length(x, y, z, dx, dy, dz, length)
    local hit = collision_find_surface_on_ray(x, y, z, dx * length, dy * length, dz * length, 3)
    if hit and hit.surface then
        local hx, hy, hz = hit.hitPos.x - x, hit.hitPos.y - y, hit.hitPos.z - z
        return math.sqrt(hx * hx + hy * hy + hz * hz)
    end
    return length
end

local ATTACKABLE = INTERACT_BOUNCE_TOP | INTERACT_BOUNCE_TOP2 | INTERACT_HIT_FROM_BELOW | INTERACT_BREAKABLE | INTERACT_KOOPA
local LISTS = {OBJ_LIST_GENACTOR, OBJ_LIST_PUSHABLE, OBJ_LIST_DESTRUCTIVE, OBJ_LIST_SURFACE}

function goku_attack_segment(ax, ay, az, bx, by, bz, radius, attack, tag)
    local hit = false
    for _, list in ipairs(LISTS) do
        local o = obj_get_first(list)
        while o do
            if o.oInteractType & ATTACKABLE ~= 0 and o.oGokuHitTag ~= tag and o.oIntangibleTimer == 0 then
                local d = seg_dist(o.oPosX, o.oPosY + o.hitboxHeight * 0.5, o.oPosZ, ax, ay, az, bx, by, bz)
                if d <= radius + o.hitboxRadius then
                    o.oInteractStatus = INT_STATUS_INTERACTED | INT_STATUS_WAS_ATTACKED | attack
                    o.oGokuHitTag = tag
                    hit = true
                end
            end
            o = obj_get_next(o)
        end
    end
    return hit
end

function goku_attack_local_player(o, ax, ay, az, bx, by, bz, radius, damage)
    local m = gMarioStates[0]
    if gServerSettings.playerInteractions ~= PLAYER_INTERACTIONS_PVP then return end
    if o.oGokuOwner == network_global_index_from_local(0) then return end
    local seen = gGoku[0].tagSeen
    if seen[o] == o.oGokuTag then return end
    if m.invincTimer > 0 or m.action & ACT_FLAG_INTANGIBLE ~= 0 or m.health <= 0xFF then return end
    if seg_dist(m.pos.x, m.pos.y + 80, m.pos.z, ax, ay, az, bx, by, bz) > radius + 50 then return end
    seen[o] = o.oGokuTag
    m.hurtCounter = m.hurtCounter + damage * 4
    m.invincTimer = 30
    m.faceAngle.y = atan2s(bz - az, bx - ax) + 0x8000
    m.forwardVel = -36
    set_mario_action(m, m.action & ACT_FLAG_AIR ~= 0 and ACT_HARD_BACKWARD_AIR_KB or ACT_HARD_BACKWARD_GROUND_KB, 0)
end

function goku_gone(m)
    return m.playerIndex ~= 0 and is_player_active(m) == 0
end

function goku_alive(o)
    return o ~= nil and o.activeFlags ~= ACTIVE_FLAG_DEACTIVATED
end
