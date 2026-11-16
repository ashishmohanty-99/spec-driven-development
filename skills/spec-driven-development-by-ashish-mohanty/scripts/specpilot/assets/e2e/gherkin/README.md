# Acceptance scenarios (Gherkin)

`sdd gen-tests <feature>` writes one `<feature>.feature` file here from the Given / When / Then
scenarios in the spec. Every scenario is tagged with the id of the requirement it proves, which is
how `sdd verify` traces it.

Feature files are language-neutral. Run them with the Cucumber implementation for your stack and
write step definitions in your own language:

| Stack | Runner |
|---|---|
| Java / Kotlin | Cucumber-JVM |
| C# / .NET | Reqnroll (SpecFlow) |
| Go | godog |
| Ruby | Cucumber |
| PHP | Behat |
| Python | behave or pytest-bdd |
| JavaScript / TypeScript | cucumber-js |
| Rust | cucumber-rs |
| Swift / Kotlin mobile | XCTest-Gherkin, Cucumber-Android |

Then set the command that runs them in `.sdd/config.json` under `commands.e2e`
(for example `"mvn -q verify"` or `"godog run tests/e2e"`), so `sdd regression` includes them.

Only the block between the GENERATED markers is rewritten on regeneration. Add your own scenarios
below it. Never put passwords or tokens in a feature file; read them from the environment in your
step definitions.
