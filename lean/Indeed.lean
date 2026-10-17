import Lean

/-!
The executable and its proofs share this catalogue and selector.

The formal contract is syntactic membership in a curated phrase pool. It does
not claim that a phrase is true, that a detector chose the correct language,
or that the caller's random draws have any statistical property.
-/

namespace Indeed

inductive Locale where
  | en | zh | ja | ko | es | fr | de | pt | ru | ar
  deriving Repr, BEq, DecidableEq

def Locale.code : Locale → String
  | .en => "en"
  | .zh => "zh"
  | .ja => "ja"
  | .ko => "ko"
  | .es => "es"
  | .fr => "fr"
  | .de => "de"
  | .pt => "pt"
  | .ru => "ru"
  | .ar => "ar"

def Locale.parse : String → Option Locale
  | "en" => some .en
  | "zh" => some .zh
  | "ja" => some .ja
  | "ko" => some .ko
  | "es" => some .es
  | "fr" => some .fr
  | "de" => some .de
  | "pt" => some .pt
  | "ru" => some .ru
  | "ar" => some .ar
  | _ => none

def locales : List Locale := [.en, .zh, .ja, .ko, .es, .fr, .de, .pt, .ru, .ar]

/-- The only source of reply text, used by both `catalog` and `reply`. -/
def pool : Locale → List String
  | .en => ["Indeed.", "Exactly.", "That makes a lot of sense.",
            "You're absolutely right.", "I couldn't agree more."]
  | .zh => ["确实。", "太对了。", "你说得很有道理。", "确实是这样。", "完全同意。"]
  | .ja => ["確かに。", "その通りです。", "おっしゃる通りです。", "同感です。", "まさにそうですね。"]
  | .ko => ["맞아요.", "정말 그렇네요.", "말씀에 동의해요.", "정확해요.", "정말 일리 있는 말씀이에요."]
  | .es => ["Así es.", "Exactamente.", "Tiene mucho sentido.",
            "Tienes toda la razón.", "No podría estar más de acuerdo."]
  | .fr => ["En effet.", "Exactement.", "C'est tout à fait logique.",
            "Vous avez tout à fait raison.", "Je suis entièrement d'accord."]
  | .de => ["In der Tat.", "Ganz genau.", "Das ergibt Sinn.",
            "Du hast völlig recht.", "Dem stimme ich vollkommen zu."]
  | .pt => ["De fato.", "Exatamente.", "Faz todo o sentido.",
            "Você tem toda a razão.", "Concordo plenamente."]
  | .ru => ["Действительно.", "Именно так.", "В этом есть смысл.",
            "Вы совершенно правы.", "Полностью согласен."]
  | .ar => ["بالفعل.", "بالضبط.", "هذا منطقي جدًا.", "أنت محق تمامًا.", "أتفق معك تمامًا."]

/-- Every supported language has at least one reply. -/
theorem pool_length_pos (locale : Locale) : 0 < (pool locale).length := by
  cases locale <;> decide

/-- No curated reply is the empty string. -/
theorem pool_member_nonempty (locale : Locale) (text : String)
    (h : text ∈ pool locale) : text ≠ "" := by
  have noEmpty : "" ∉ pool locale := by
    cases locale <;> decide
  intro empty
  subst text
  exact noEmpty h

/-- Normalizing an arbitrary natural draw makes every selection in bounds. -/
def selectionIndex (locale : Locale) (draw : Nat) : Nat :=
  draw % (pool locale).length

theorem selectionIndex_lt (locale : Locale) (draw : Nat) :
    selectionIndex locale draw < (pool locale).length :=
  Nat.mod_lt draw (pool_length_pos locale)

/-- The runtime's selector: a total, bounds-checked lookup with no fallback. -/
def selectReply (locale : Locale) (draw : Nat) : String :=
  (pool locale)[selectionIndex locale draw]'(selectionIndex_lt locale draw)

/-- Every selected reply belongs to the pool for the supplied locale. -/
theorem selectReply_mem (locale : Locale) (draw : Nat) :
    selectReply locale draw ∈ pool locale := by
  exact List.getElem_mem (selectionIndex_lt locale draw)

/-- Every selected reply has content. -/
theorem selectReply_nonempty (locale : Locale) (draw : Nat) :
    selectReply locale draw ≠ "" :=
  pool_member_nonempty locale _ (selectReply_mem locale draw)

/-- Equivalent inputs yield identical text; randomness is supplied externally. -/
theorem selectReply_deterministic (locale₁ locale₂ : Locale) (draw₁ draw₂ : Nat)
    (sameLocale : locale₁ = locale₂) (sameDraw : draw₁ = draw₂) :
    selectReply locale₁ draw₁ = selectReply locale₂ draw₂ := by
  subst locale₂
  subst draw₂
  rfl

end Indeed
