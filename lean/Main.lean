import Indeed

open Lean Indeed

private def catalogJson : Json :=
  Json.mkObj (locales.map fun locale =>
    (locale.code, Json.arr ((pool locale).map Json.str).toArray))

private def replyJson (locale : Locale) (draw : Nat) : Json :=
  Json.mkObj [
    ("locale", toJson locale.code),
    ("index", toJson (selectionIndex locale draw)),
    ("text", toJson (selectReply locale draw)),
    ("pool_size", toJson (pool locale).length)]

private def output (json : Json) : IO UInt32 := do
  (← IO.getStdout).putStrLn json.compress
  return 0

private def fail (message : String) : IO UInt32 := do
  (← IO.getStderr).putStrLn (Json.mkObj [("error", Json.str message)]).compress
  return 2

private def help : String :=
  "indeed-core — verified agreement selection\n\n" ++
  "Usage:\n" ++
  "  indeed-core catalog\n" ++
  "  indeed-core reply <locale> <draw>\n\n" ++
  "Locales: en zh ja ko es fr de pt ru ar\n" ++
  "draw: an unsigned decimal natural number; index = draw mod pool_size\n" ++
  "Successful commands emit a compact JSON object on stdout.\n" ++
  "Invalid commands emit a JSON error on stderr and exit with status 2."

def main (args : List String) : IO UInt32 := do
  match args with
  | ["--help"] | ["-h"] | ["help"] =>
    (← IO.getStdout).putStrLn help
    return 0
  | ["catalog"] => output catalogJson
  | ["reply", code, rawDraw] =>
    match Locale.parse code with
    | none => fail "unsupported locale; expected one of: en zh ja ko es fr de pt ru ar"
    | some locale =>
      if rawDraw.isEmpty || !rawDraw.toList.all Char.isDigit then
        fail "draw must be an unsigned decimal natural number"
      else
        match rawDraw.toNat? with
        | none => fail "draw must be an unsigned decimal natural number"
        | some draw => output (replyJson locale draw)
  | _ => fail "usage: indeed-core catalog | indeed-core reply <locale> <draw> | indeed-core --help"
