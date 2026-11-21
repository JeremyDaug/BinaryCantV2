#!/usr/bin/env python3
"""One-time generator used to seed the v2.2 lexicon growth.

It appends new roots to lexicon.csv (existing roots keep their IDs) and writes
cant/english/en_lexicon.csv.  After seeding, the two CSV files are authoritative;
edit them directly.  Re-running this script is idempotent (it rebuilds from the
v2.1 base rows plus the table below).

English spec mini-syntax (per root, space separated):
    POS.cat:word[@field=Value,...][#form=x,...][!]
POS: n noun, pl place-noun (no article), v verb, a adjective, adv adverb,
     rv relation verb (S rel O), p preposition relation, rn relation noun ("the X of"),
     pron pronoun, dem demonstrative, q quantity determiner, tadv time adverb
'!' = accepted when parsing English but never chosen when rendering.
"""

import csv
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from cant.semantic import make_root  # noqa: E402

CATS = ["obj", "rel", "act", "loc"]

# English for the 43 v2.1 roots ---------------------------------------------------
EN_EXISTING = {
    "null": "v.act:happen",
    "nothing": "n.obj:nothing",
    "existence": "v.act:exist n.obj:existence n.loc:universe",
    "abstraction": "n.obj:idea",
    "self": "pron.obj:i#obj=me,poss=my,pl=we,plobj=us,plposs=our",
    "addressee": "pron.obj:you#obj=you,poss=your,pl=you,plobj=you,plposs=your",
    "other": "pron.obj:they#obj=them,poss=their,pl=they,plobj=them,plposs=their "
             "pron.obj:he#obj=him,poss=his! pron.obj:she#obj=her,poss=her! pron.obj:it#obj=it,poss=its!",
    "this": "dem.obj:this#pl=these pl.loc:here",
    "that": "dem.obj:that#pl=those pl.loc:there",
    "possession": "rv.rel:have#3sg=has,past=had,pp=had,ing=having n.obj:possession v.act:own rv.rel:own!",
    "manipulator": "n.obj:hand v.act:manipulate",
    "mover": "n.obj:leg v.act:move v.act:run@degree=Large#past=ran,pp=run,ing=running n.obj:foot#pl=feet!",
    "auditory_communicator": "n.obj:mouth v.act:say#3sg=says,past=said,pp=said v.act:speak#past=spoke,pp=spoken! "
                             "v.act:talk! n.loc:tongue",
    "auditory_listener": "n.obj:ear v.act:hear#past=heard,pp=heard v.act:listen! n.loc:ears!",
    "contact_sensor": "n.obj:skin! v.act:touch v.act:feel#past=felt,pp=felt!",
    "olfactory_sensor": "n.obj:nose v.act:smell",
    "sustenance_orifice": "v.act:eat#past=ate,pp=eaten",
    "waste_orifice": "",
    "controller": "n.obj:brain v.act:control#past=controlled,pp=controlled,ing=controlling",
    "power_pump": "n.obj:heart v.act:pump",
    "energy_storage": "n.obj:battery",
    "sophont": "n.obj:person#pl=people n.obj:human!",
    "animal": "n.obj:animal",
    "uncontrolled": "",
    "inanimate_object": "n.obj:object",
    "parent": "n.obj:parent rn.rel:parent n.obj:mother! n.obj:father!",
    "kin": "n.obj:family rn.rel:family",
    "partner": "n.obj:partner rn.rel:partner",
    "mentor": "n.obj:teacher v.act:teach#past=taught,pp=taught rn.rel:teacher",
    "friend": "n.obj:friend rn.rel:friend",
    "greeting": "n.obj:greeting v.act:greet",
    "cover": "n.obj:shirt v.act:wear#past=wore,pp=worn n.obj:clothing!",
    "tool": "n.obj:tool",
    "instrument": "n.obj:instrument",
    "interface": "n.obj:interface",
    "dwelling": "n.obj:house pl.loc:home",
    "music": "n.obj:music",
    "musician": "n.obj:musician",
    "band": "n.obj:band",
    "height": "a.obj:tall@degree=Large a.obj:short@degree=Small n.obj:height",
    "size": "a.obj:big@degree=Large a.obj:small@degree=Small n.obj:size v.act:grow#past=grew,pp=grown "
            "a.obj:large@degree=Large! a.obj:little@degree=Small!",
    "pleasure": "v.act:enjoy rv.rel:like n.obj:pleasure",
    "everything": "n.obj:everything",
}

# New roots: domain -> cluster -> [(key, obj, rel, act, loc, english)] ---------------
NEW = {
 0: {  # core
  2: [("someone", "entity (someone, something)", "", "", "somewhere", "n.obj:thing n.obj:something! n.obj:someone!")],
  4: [("sameness", "sameness", "same as", "matching", "", "rn.rel:same!"),
      ("difference", "difference", "different from", "differing", "", "n.obj:difference"),
      ("kind", "kind (type, category)", "kind of", "classifying", "", "n.obj:kind")],
  5: [("truth", "truth", "true of", "verifying", "", "n.obj:truth"),
      ("falsehood", "falsehood (a lie)", "", "lying (deceiving)", "", "n.obj:lie")],
  6: [("cause", "cause (reason)", "causes (S causes O)", "causing", "", "n.obj:reason v.act:cause"),
      ("purpose", "purpose", "for (S is for O)", "intending", "", "n.obj:purpose p.rel:for"),
      ("effect", "effect (result)", "results from", "affecting", "", "n.obj:result")],
  7: [("possibility", "possibility", "", "being possible", "", "n.obj:chance"),
      ("ability", "ability", "", "being able", "", "n.obj:ability"),
      ("necessity", "necessity (need)", "needs (S needs O)", "needing", "", "rv.rel:need n.obj:need!")],
 },
 1: {  # body
  0: [("arm", "arm (manipulator limb)", "", "reaching", "", "n.obj:arm v.act:reach")],
  1: [("telling", "account (report)", "tells (S tells O)", "telling", "", "v.act:tell#past=told,pp=told"),
      ("asking", "question", "asks (S asks O)", "asking", "", "n.obj:question v.act:ask"),
      ("answering", "answer", "answers (S answers O)", "answering", "", "n.obj:answer v.act:answer"),
      ("calling", "call", "", "calling", "", "v.act:call n.obj:call"),
      ("singing", "song", "", "singing", "", "n.obj:song v.act:sing#past=sang,pp=sung"),
      ("shouting", "shout", "", "shouting", "", "v.act:shout")],
  2: [("visual_sensor", "visual sensor (eye)", "sees (S sees O)", "seeing", "in sight",
       "n.obj:eye v.act:see#past=saw,pp=seen,ing=seeing"),
      ("gustatory_sensor", "gustatory sensor", "", "tasting", "", "v.act:taste"),
      ("looking", "gaze (look)", "", "looking", "", "v.act:look v.act:watch!"),
      ("showing", "display", "", "showing", "", "v.act:show#pp=shown")],
  3: [("drinking", "drink (liquid sustenance)", "", "drinking", "", "v.act:drink#past=drank,pp=drunk n.obj:drink"),
      ("breathing", "breath", "", "breathing", "", "n.obj:breath v.act:breathe")],
  5: [("head", "head", "", "", "", "n.obj:head"),
      ("torso", "torso (body)", "", "", "", "n.obj:body"),
      ("skin", "skin", "", "", "", "n.obj:skin"),
      ("bone", "bone", "", "", "", "n.obj:bone"),
      ("blood", "blood", "", "bleeding", "", "n.obj:blood v.act:bleed#past=bled,pp=bled"),
      ("hair", "hair", "", "", "", "n.obj:hair"),
      ("tooth", "tooth", "", "biting", "", "n.obj:tooth#pl=teeth v.act:bite#past=bit,pp=bitten,ing=biting")],
  6: [("life", "life", "", "living", "alive", "n.obj:life#pl=lives v.act:live"),
      ("death", "death", "", "dying", "", "n.obj:death v.act:die#ing=dying"),
      ("sleep", "sleep", "", "sleeping", "asleep", "v.act:sleep#past=slept,pp=slept"),
      ("waking", "", "", "waking", "awake", "v.act:wake#past=woke,pp=woken"),
      ("health", "health", "", "healing", "", "n.obj:health v.act:heal a.obj:healthy@degree=Large"),
      ("sickness", "sickness", "", "being sick", "", "a.obj:sick@degree=Large n.obj:sickness"),
      ("rest", "rest", "", "resting", "", "v.act:rest"),
      ("waiting", "wait", "waits for (S waits for O)", "waiting", "", "v.act:wait")],
 },
 2: {  # beings
  1: [("dog", "dog", "", "", "", "n.obj:dog"), ("cat", "cat", "", "", "", "n.obj:cat"),
      ("bird", "bird", "", "", "", "n.obj:bird"), ("fish", "fish", "", "fishing", "", "n.obj:fish#pl=fish"),
      ("horse", "horse", "", "", "", "n.obj:horse"), ("cow", "cow", "", "", "", "n.obj:cow"),
      ("pig", "pig", "", "", "", "n.obj:pig"), ("sheep", "sheep", "", "", "", "n.obj:sheep#pl=sheep"),
      ("insect", "insect", "", "", "", "n.obj:insect n.obj:bug!"), ("snake", "snake", "", "", "", "n.obj:snake"),
      ("mouse", "mouse", "", "", "", "n.obj:mouse#pl=mice")],
  2: [("plant", "plant", "", "planting", "", "n.obj:plant v.act:plant!"),
      ("tree", "tree", "", "", "", "n.obj:tree"), ("flower", "flower", "", "flowering", "", "n.obj:flower"),
      ("grass", "grass", "", "", "", "n.obj:grass"), ("fruit", "fruit", "", "", "", "n.obj:fruit"),
      ("seed", "seed", "", "", "", "n.obj:seed"), ("leaf", "leaf", "", "", "", "n.obj:leaf#pl=leaves")],
  3: [("man", "man", "", "", "", "n.obj:man#pl=men"), ("woman", "woman", "", "", "", "n.obj:woman#pl=women"),
      ("child", "child", "child of (S is child of O)", "", "", "n.obj:child#pl=children rn.rel:child#pl=children "
       "n.obj:son! n.obj:daughter! n.obj:kid!"),
      ("adult", "adult", "", "", "", "n.obj:adult")],
  4: [("machine", "machine", "", "", "", "n.obj:machine"), ("computer", "computer", "", "computing", "", "n.obj:computer"),
      ("robot", "robot (servitor)", "", "", "", "n.obj:robot n.obj:servitor!")],
  5: [("group", "group", "member of (S is member of O)", "gathering", "", "n.obj:group n.obj:team! v.act:gather")],
 },
 3: {  # social
  0: [("sibling", "sibling", "sibling of (S is sibling of O)", "", "", "n.obj:sibling rn.rel:sibling n.obj:brother! n.obj:sister!")],
  1: [("student", "student", "student of", "studying", "", "n.obj:student v.act:study v.act:learn!")],
  2: [("enemy", "enemy", "enemy of (S is enemy of O)", "opposing", "", "n.obj:enemy rn.rel:enemy"),
      ("stranger", "stranger", "", "", "", "n.obj:stranger")],
  3: [("help", "help (aid)", "helper of", "helping", "", "v.act:help n.obj:help!"),
      ("fight", "fight", "fights (S fights O)", "fighting", "", "v.act:fight#past=fought,pp=fought n.obj:fight!"),
      ("meeting", "meeting", "", "meeting", "", "v.act:meet#past=met,pp=met n.obj:meeting"),
      ("thanks", "thanks", "", "thanking", "", "v.act:thank")],
  4: [("leader", "leader", "leads (S leads O)", "leading", "", "n.obj:leader v.act:lead#past=led,pp=led n.obj:king!"),
      ("law", "law (rule)", "", "ruling", "", "n.obj:law n.obj:rule"),
      ("command", "command (order)", "", "commanding", "", "n.obj:order v.act:command")],
  5: [("money", "money", "", "", "", "n.obj:money"),
      ("buying", "purchase", "", "buying", "", "v.act:buy#past=bought,pp=bought"),
      ("selling", "sale", "", "selling", "", "v.act:sell#past=sold,pp=sold"),
      ("paying", "payment", "pays (S pays O)", "paying", "", "v.act:pay#past=paid,pp=paid"),
      ("price", "price", "costs", "", "", "n.obj:price")],
  6: [("name", "name", "", "naming", "", "n.obj:name v.act:name!"), ("word", "word", "", "", "", "n.obj:word"),
      ("language", "language", "", "", "", "n.obj:language"), ("story", "story", "", "narrating", "", "n.obj:story"),
      ("message", "message", "", "messaging", "", "n.obj:message n.obj:letter!")],
 },
 4: {  # artifacts
  0: [("shoe", "shoe", "", "", "", "n.obj:shoe"), ("hat", "hat", "", "", "", "n.obj:hat")],
  1: [("knife", "knife", "", "", "", "n.obj:knife#pl=knives"), ("weapon", "weapon", "", "", "", "n.obj:weapon n.obj:gun!")],
  2: [("screen", "screen", "", "", "", "n.obj:screen"), ("button", "button", "", "pressing", "", "n.obj:button v.act:press")],
  3: [("door", "door", "", "", "", "n.obj:door"), ("room", "room", "", "", "", "n.obj:room"),
      ("wall", "wall", "", "", "", "n.obj:wall"), ("window", "window", "", "", "", "n.obj:window"),
      ("building", "building", "", "", "", "n.obj:building"), ("bridge", "bridge", "", "", "", "n.obj:bridge")],
  4: [("container", "container", "", "", "", "n.obj:container"), ("box", "box", "", "", "", "n.obj:box"),
      ("cup", "cup", "", "", "", "n.obj:cup"), ("bag", "bag", "", "", "", "n.obj:bag"),
      ("bottle", "bottle", "", "", "", "n.obj:bottle")],
  5: [("table", "table", "", "", "", "n.obj:table"), ("chair", "chair", "", "", "", "n.obj:chair"),
      ("bed", "bed", "", "", "", "n.obj:bed")],
  6: [("vehicle", "vehicle", "", "driving", "", "n.obj:car v.act:drive#past=drove,pp=driven n.obj:vehicle!"),
      ("boat", "boat", "", "sailing", "", "n.obj:boat n.obj:ship!"),
      ("aircraft", "aircraft", "", "", "", "n.obj:plane"), ("wheel", "wheel", "", "rolling", "", "n.obj:wheel")],
  7: [("book", "book", "", "", "", "n.obj:book"), ("paper", "paper", "", "", "", "n.obj:paper")],
  8: [("lamp", "lamp", "", "", "", "n.obj:lamp"), ("clock", "clock", "", "", "", "n.obj:clock"),
      ("phone", "phone", "", "phoning", "", "n.obj:phone")],
 },
 5: {  # arts
  1: [("picture", "picture (image)", "", "drawing", "", "n.obj:picture v.act:draw#past=drew,pp=drawn n.obj:image!"),
      ("paint", "paint", "", "painting", "", "n.obj:paint v.act:paint!"),
      ("colour", "colour (as a concept)", "", "colouring", "", "n.obj:colour n.obj:color!")],
  2: [("game", "game", "", "playing", "", "n.obj:game v.act:play"), ("toy", "toy", "", "", "", "n.obj:toy"),
      ("ball", "ball", "", "", "", "n.obj:ball")],
  3: [("dance", "dance", "", "dancing", "", "v.act:dance n.obj:dance!")],
 },
 6: {  # qualities (scalar adjectives use the degree field)
  0: [("length", "length", "longer than", "lengthening", "", "a.obj:long@degree=Large n.obj:length"),
      ("weight", "weight", "heavier than", "weighing", "", "a.obj:heavy@degree=Large a.obj:light@degree=Small n.obj:weight")],
  1: [("temperature", "temperature", "hotter than", "heating", "",
       "a.obj:hot@degree=Large a.obj:cold@degree=Small a.obj:warm@degree=Medium n.obj:temperature")],
  2: [("speed", "speed", "faster than", "accelerating", "",
       "a.obj:fast@degree=Large a.obj:slow@degree=Small adv.obj:quickly@degree=Large adv.obj:slowly@degree=Small "
       "a.obj:quick@degree=Large!")],
  3: [("age", "age", "older than", "aging", "", "a.obj:old@degree=Large a.obj:young@degree=Small n.obj:age"),
      ("novelty", "novelty", "newer than", "renewing", "", "a.obj:new@degree=Large")],
  4: [("goodness", "goodness", "better than", "improving", "",
       "a.obj:good@degree=Large#cmp=better a.obj:bad@degree=Small#cmp=worse adv.obj:well@degree=Large "
       "adv.obj:badly@degree=Small"),
      ("beauty", "beauty", "more beautiful than", "", "", "a.obj:beautiful@degree=Large a.obj:ugly@degree=Small a.obj:pretty@degree=Large!"),
      ("importance", "importance", "", "", "", "a.obj:important@degree=Large")],
  5: [("difficulty", "difficulty", "harder than", "", "", "a.obj:difficult@degree=Large a.obj:easy@degree=Small")],
  6: [("brightness", "brightness", "brighter than", "shining", "", "a.obj:bright@degree=Large a.obj:dark@degree=Small v.act:shine#past=shone,pp=shone"),
      ("loudness", "loudness", "louder than", "", "", "a.obj:loud@degree=Large a.obj:quiet@degree=Small"),
      ("hardness", "hardness", "harder than", "hardening", "", "a.obj:hard@degree=Large a.obj:soft@degree=Small"),
      ("wetness", "wetness", "wetter than", "wetting", "", "a.obj:wet@degree=Large a.obj:dry@degree=Small"),
      ("cleanliness", "cleanliness", "cleaner than", "cleaning", "", "a.obj:clean@degree=Large a.obj:dirty@degree=Small v.act:clean!"),
      ("fullness", "fullness", "fuller than", "filling", "", "a.obj:full@degree=Large a.obj:empty@degree=Small v.act:fill")],
  7: [("male", "male", "", "", "", "a.obj:male@degree=Large"), ("female", "female", "", "", "", "a.obj:female@degree=Large")],
  8: [("strength", "strength", "stronger than", "strengthening", "", "a.obj:strong@degree=Large a.obj:weak@degree=Small"),
      ("wealth", "wealth", "richer than", "", "", "a.obj:rich@degree=Large a.obj:poor@degree=Small")],
  9: [("correctness", "correctness", "", "correcting", "", "a.obj:right@degree=Large a.obj:wrong@degree=Small a.obj:correct@degree=Large!")],
  10: [("danger", "danger", "more dangerous than", "endangering", "", "a.obj:dangerous@degree=Large a.obj:safe@degree=Small")],
 },
 7: {  # mind
  0: [("pain", "pain", "", "hurting", "", "n.obj:pain v.act:hurt#past=hurt,pp=hurt")],
  1: [("joy", "joy", "", "rejoicing", "", "a.obj:happy@degree=Large n.obj:joy"),
      ("sorrow", "sorrow", "", "grieving", "", "a.obj:sad@degree=Large v.act:cry"),
      ("fear", "fear", "fears (S fears O)", "fearing", "", "a.obj:afraid@degree=Large rv.rel:fear n.obj:fear!"),
      ("anger", "anger", "angry at", "raging", "", "a.obj:angry@degree=Large"),
      ("love", "love", "loves (S loves O)", "loving", "", "rv.rel:love n.obj:love"),
      ("hate", "hatred", "hates (S hates O)", "hating", "", "rv.rel:hate"),
      ("surprise", "surprise", "", "surprising", "", "a.obj:surprised@degree=Large n.obj:surprise")],
  2: [("knowledge", "knowledge", "knows (S knows O)", "learning (coming to know)", "",
       "rv.rel:know#past=knew,pp=known n.obj:knowledge"),
      ("thought", "thought", "thinks of", "thinking", "", "v.act:think#past=thought,pp=thought n.obj:thought"),
      ("belief", "belief", "believes (S believes O)", "believing", "", "rv.rel:believe n.obj:belief"),
      ("memory", "memory", "remembers (S remembers O)", "remembering", "", "rv.rel:remember n.obj:memory"),
      ("understanding", "understanding", "understands", "understanding", "", "rv.rel:understand#past=understood,pp=understood"),
      ("forgetting", "", "forgets", "forgetting", "", "rv.rel:forget#past=forgot,pp=forgotten,ing=forgetting")],
  3: [("desire", "desire", "wants (S wants O)", "wishing", "", "rv.rel:want n.obj:desire v.act:wish!"),
      ("intent", "plan (intent)", "", "planning", "", "n.obj:plan v.act:plan#past=planned,pp=planned,ing=planning"),
      ("choice", "choice", "chooses", "choosing", "", "v.act:choose#past=chose,pp=chosen,ing=choosing n.obj:choice"),
      ("attempt", "attempt", "", "trying", "", "v.act:try")],
  4: [("attention", "attention", "notices", "noticing", "", "v.act:notice n.obj:attention"),
      ("care", "care", "cares for", "caring", "", "v.act:care")],
 },
 8: {  # motion and transfer
  0: [("travel", "journey", "", "going", "en route", "v.act:go#3sg=goes,past=went,pp=gone v.act:travel! n.obj:journey"),
      ("arrival", "arrival", "", "coming", "destination", "v.act:come#past=came,pp=come,ing=coming v.act:arrive!"),
      ("departure", "departure", "leaves (S leaves O)", "leaving", "", "v.act:leave#past=left,pp=left,ing=leaving"),
      ("return", "return", "", "returning", "", "v.act:return"),
      ("walking", "walk", "", "walking", "", "v.act:walk"),
      ("flying", "flight", "", "flying", "", "v.act:fly#3sg=flies,past=flew,pp=flown"),
      ("swimming", "swim", "", "swimming", "", "v.act:swim#past=swam,pp=swum,ing=swimming"),
      ("falling", "fall", "", "falling", "", "v.act:fall#past=fell,pp=fallen"),
      ("jumping", "jump", "", "jumping", "", "v.act:jump"),
      ("climbing", "climb", "", "climbing", "", "v.act:climb")],
  1: [("giving", "gift", "gives (S gives O)", "giving", "", "v.act:give#past=gave,pp=given,ing=giving n.obj:gift"),
      ("taking", "", "takes", "taking", "", "v.act:take#past=took,pp=taken,ing=taking"),
      ("bringing", "", "", "bringing", "", "v.act:bring#past=brought,pp=brought"),
      ("sending", "", "", "sending", "", "v.act:send#past=sent,pp=sent"),
      ("carrying", "load", "", "carrying", "", "v.act:carry"),
      ("receiving", "", "", "receiving", "", "v.act:receive v.act:get#past=got,pp=gotten,ing=getting!")],
  2: [("putting", "", "", "putting (placing)", "", "v.act:put#past=put,pp=put,ing=putting"),
      ("holding", "grip", "holds", "holding", "", "v.act:hold#past=held,pp=held"),
      ("dropping", "", "", "dropping", "", "v.act:drop#past=dropped,pp=dropped,ing=dropping"),
      ("throwing", "throw", "", "throwing", "", "v.act:throw#past=threw,pp=thrown"),
      ("pulling", "", "", "pulling", "", "v.act:pull"),
      ("pushing", "", "", "pushing", "", "v.act:push"),
      ("keeping", "", "keeps", "keeping", "", "v.act:keep#past=kept,pp=kept")],
  3: [("sitting", "seat", "", "sitting", "seated", "v.act:sit#past=sat,pp=sat,ing=sitting"),
      ("standing", "", "", "standing", "upright", "v.act:stand#past=stood,pp=stood"),
      ("reclining", "", "", "lying down", "", "v.act:lie#past=lay,pp=lain,ing=lying")],
  4: [("path", "path (way)", "", "", "on the way", "n.obj:way n.obj:path!")],
 },
 9: {  # making and change
  0: [("making", "product", "", "making", "", "v.act:make#past=made,pp=made,ing=making v.act:create!"),
      ("construction", "", "", "building", "", "v.act:build#past=built,pp=built"),
      ("writing", "writing (text)", "", "writing", "", "v.act:write#past=wrote,pp=written,ing=writing"),
      ("reading", "", "reads", "reading", "", "v.act:read#past=read,pp=read"),
      ("cooking", "", "", "cooking", "", "v.act:cook")],
  1: [("breaking", "break", "", "breaking", "", "v.act:break#past=broke,pp=broken"),
      ("cutting", "cut", "", "cutting", "", "v.act:cut#past=cut,pp=cut,ing=cutting"),
      ("killing", "", "", "killing", "", "v.act:kill"),
      ("burning", "", "", "burning", "", "v.act:burn")],
  2: [("change", "change", "", "changing", "", "v.act:change n.obj:change!"),
      ("beginning", "beginning", "", "beginning (starting)", "", "v.act:start v.act:begin#past=began,pp=begun,ing=beginning!"),
      ("ending", "end", "", "ending (stopping)", "", "v.act:stop#past=stopped,pp=stopped,ing=stopping n.obj:end v.act:finish! v.act:end!"),
      ("continuing", "", "", "continuing", "", "v.act:continue")],
  3: [("using", "use", "uses (S uses O)", "using", "", "v.act:use"),
      ("work", "work (labour)", "", "working", "", "v.act:work n.obj:job"),
      ("repair", "repair", "", "repairing", "", "v.act:fix")],
  4: [("opening", "opening", "", "opening", "", "v.act:open"), ("closing", "", "", "closing", "", "v.act:close v.act:shut!")],
  5: [("finding", "find", "", "finding", "", "v.act:find#past=found,pp=found"),
      ("losing", "loss", "", "losing", "", "v.act:lose#past=lost,pp=lost,ing=losing"),
      ("searching", "search", "", "searching", "", "v.act:search"),
      ("hiding", "", "", "hiding", "hidden", "v.act:hide#past=hid,pp=hidden,ing=hiding")],
 },
 10: {  # places and nature
  0: [("place", "place", "", "", "somewhere (a place)", "n.obj:place"), ("city", "city", "", "", "", "n.obj:city n.obj:town!"),
      ("village", "village", "", "", "", "n.obj:village"), ("country", "country", "", "", "", "n.obj:country"),
      ("world", "world", "", "", "", "n.obj:world")],
  1: [("ground", "ground (earth)", "", "", "", "n.obj:ground n.obj:earth!"), ("mountain", "mountain", "", "", "", "n.obj:mountain"),
      ("field", "field", "", "", "", "n.obj:field"), ("forest", "forest", "", "", "", "n.obj:forest n.obj:wood!"),
      ("desert", "desert", "", "", "", "n.obj:desert")],
  2: [("water", "water", "", "watering", "", "n.obj:water"), ("river", "river", "", "", "", "n.obj:river"),
      ("sea", "sea", "", "", "", "n.obj:sea n.obj:ocean!"), ("lake", "lake", "", "", "", "n.obj:lake"),
      ("rain", "rain", "", "raining", "", "n.obj:rain v.act:rain!"), ("snow", "snow", "", "snowing", "", "n.obj:snow")],
  3: [("sky", "sky", "", "", "", "n.obj:sky"), ("sun", "sun", "", "", "", "n.obj:sun"), ("moon", "moon", "", "", "", "n.obj:moon"),
      ("star", "star", "", "", "", "n.obj:star"), ("cloud", "cloud", "", "", "", "n.obj:cloud"),
      ("wind", "wind", "", "blowing", "", "n.obj:wind"), ("light", "light", "", "illuminating", "", "n.obj:light")],
  4: [("stone", "stone", "", "", "", "n.obj:stone n.obj:rock!"), ("timber", "wood (material)", "", "", "", "n.obj:timber"),
      ("metal", "metal", "", "", "", "n.obj:metal"), ("fire", "fire", "", "", "", "n.obj:fire"),
      ("air", "air", "", "", "", "n.obj:air")],
  5: [("school", "school", "", "", "", "n.obj:school"), ("shop", "shop (market)", "", "shopping", "", "n.obj:shop n.obj:store! n.obj:market!"),
      ("road", "road", "", "", "", "n.obj:road n.obj:street!"), ("hospital", "hospital", "", "", "", "n.obj:hospital"),
      ("temple", "temple", "", "", "", "n.obj:temple"), ("garden", "garden", "", "gardening", "", "n.obj:garden"),
      ("farm", "farm", "", "farming", "", "n.obj:farm")],
  6: [("food", "food", "", "feeding", "", "n.obj:food n.obj:meal! v.act:feed#past=fed,pp=fed"),
      ("bread", "bread", "", "", "", "n.obj:bread"), ("meat", "meat", "", "", "", "n.obj:meat"),
      ("milk", "milk", "", "", "", "n.obj:milk"), ("egg", "egg", "", "", "", "n.obj:egg"),
      ("apple", "apple", "", "", "", "n.obj:apple")],
 },
 11: {  # time
  0: [("time", "time", "", "timing", "", "n.obj:time"), ("moment", "moment", "", "", "",
       "n.obj:moment tadv.obj:now@temporal=Present tadv.obj:then@temporal=Past tadv.obj:soon@temporal=Future"),
      ("minute", "minute", "", "", "", "n.obj:minute"), ("hour", "hour", "", "", "", "n.obj:hour"),
      ("day", "day", "", "", "", "n.obj:day tadv.obj:today@temporal=Present tadv.obj:yesterday@temporal=Past "
       "tadv.obj:tomorrow@temporal=Future"),
      ("night", "night", "", "", "", "n.obj:night tadv.obj:tonight@temporal=Present"),
      ("week", "week", "", "", "", "n.obj:week"), ("month", "month", "", "", "", "n.obj:month"),
      ("year", "year", "", "", "", "n.obj:year")],
  1: [("precedence", "", "before (S is before O)", "preceding", "earlier", "p.rel:before"),
      ("succession", "", "after (S is after O)", "following", "later", "p.rel:after"),
      ("simultaneity", "", "during (S is during O)", "", "", "p.rel:during")],
  2: [("morning", "morning", "", "", "", "n.obj:morning"), ("evening", "evening", "", "", "", "n.obj:evening")],
 },
 12: {  # quantity (determiners use the degree field)
  0: [("amount", "amount (quantity)", "more than (S exceeds O)", "", "",
       "q.obj:all@degree=Total q.obj:many@degree=Large q.obj:few@degree=Small q.obj:some@degree=Medium "
       "q.obj:no@degree=None q.obj:every@degree=Total! q.obj:much@degree=Large! n.obj:amount"),
      ("part", "part", "part of (S is part of O)", "dividing", "", "n.obj:part rn.rel:part"),
      ("whole", "whole", "", "", "", "n.obj:whole"),
      ("number", "number (concept)", "", "counting", "", "n.obj:number v.act:count")],
 },
 13: {  # spatial relations
  0: [("interior", "inside", "in (S is inside O)", "entering", "inside", "p.rel:in v.act:enter p.rel:inside! p.rel:into!"),
      ("exterior", "outside", "outside of", "exiting", "outside", "p.rel:outside v.act:exit!")],
  1: [("surface", "surface (top)", "on (S is on O)", "landing", "on top", "p.rel:on p.rel:onto!"),
      ("beneath", "underside", "under (S is under O)", "", "below", "p.rel:under p.rel:below!"),
      ("above", "upper side", "above (S is above O)", "", "above", "p.rel:above p.rel:over!")],
  2: [("position", "position", "at (S is at O)", "positioning", "at", "p.rel:at"),
      ("nearness", "vicinity", "near (S is near O)", "approaching", "nearby", "p.rel:near"),
      ("distance", "distance", "far from (S is far from O)", "", "far away", "n.obj:distance"),
      ("adjacency", "", "beside (S is beside O)", "", "", "p.rel:beside")],
  3: [("front", "front", "in front of", "", "ahead", "n.obj:front"),
      ("back", "back (rear)", "behind (S is behind O)", "", "behind", "p.rel:behind n.obj:back"),
      ("between", "", "between (S is between O)", "", "", "p.rel:between")],
  4: [("toward", "", "to (S moves toward O)", "", "", "p.rel:to p.rel:toward! p.rel:towards!"),
      ("source", "source", "from (S comes from O)", "", "", "p.rel:from"),
      ("passage", "", "through (S passes through O)", "", "", "p.rel:through"),
      ("around", "", "around (S is around O)", "circling", "", "p.rel:around")],
  5: [("accompaniment", "company", "with (S is with O)", "accompanying", "", "p.rel:with"),
      ("absence", "absence", "without (S lacks O)", "", "absent", "p.rel:without")],
 },
 14: {  # events and manner
  0: [("event", "event", "", "happening (occurring)", "", "n.obj:event v.act:occur!"),
      ("problem", "problem", "", "", "", "n.obj:problem"),
      ("manner", "manner (way of doing)", "", "", "", "n.obj:manner")],
 },
}


def main():
    with open(os.path.join(ROOT, "lexicon.csv"), newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f)]
    base = [r for r in rows if r["source"] != "proposed-v2.2"]
    assert len(base) == 43, len(base)
    keys = {r["key"] for r in base}
    used = {(int(r["domain"]), int(r["cluster"])): 0 for r in base}
    for r in base:
        k = (int(r["domain"]), int(r["cluster"]))
        if int(r["concept"]) < 1000:
            used[k] = max(used.get(k, 0), int(r["concept"]) + 1)
    out = list(base)
    en_specs = dict(EN_EXISTING)
    for d, clusters in NEW.items():
        for c, entries in clusters.items():
            for key, o, rel, act, loc, en in entries:
                assert key not in keys, key
                keys.add(key)
                idx = used.get((d, c), 0)
                used[(d, c)] = idx + 1
                senses = [o, rel, act, loc]
                out.append({"root": f"0x{make_root(d, c, idx):08X}", "key": key, "domain": d, "cluster": c,
                            "concept": idx, "object": o, "relation": rel, "action": act, "location": loc,
                            "source": "proposed-v2.2",
                            "proposed_senses": ";".join(CATS[i] for i, s in enumerate(senses) if s),
                            "notes": ""})
                en_specs[key] = en
    out.sort(key=lambda r: int(r["root"], 16))
    with open(os.path.join(ROOT, "lexicon.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(out)
    sense_of = {r["key"]: [r["object"], r["relation"], r["action"], r["location"]] for r in out}
    en_rows = []
    for key, spec in en_specs.items():
        for tok in spec.split():
            render = "no" if tok.endswith("!") else "yes"
            tok = tok.rstrip("!")
            forms = ""
            if "#" in tok:
                tok, forms = tok.split("#", 1)
            flags = ""
            if "@" in tok:
                tok, flags = tok.split("@", 1)
            head, word = tok.split(":", 1)
            pos, cat = head.split(".")
            assert sense_of[key][CATS.index(cat)], f"{key}.{cat} has no sense for English '{word}'"
            en_rows.append({"english": word, "pos": pos, "root": f"{key}.{cat}", "flags": flags.replace(",", ";"),
                            "forms": forms.replace(",", ";"), "render": render})
    with open(os.path.join(ROOT, "cant", "english", "en_lexicon.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["english", "pos", "root", "flags", "forms", "render"])
        w.writeheader()
        w.writerows(en_rows)
    print(f"lexicon roots: {len(out)}; english entries: {len(en_rows)}")


if __name__ == "__main__":
    main()
