# MacroChef: engineering decisions

```text
React -> FastAPI
  Nutrition -> parameterized catalogue reads -> Python Decimal -> serving / meal totals
  Recipes   -> original Python profile and target calculation
            -> private Node lookup -> PostgreSQL recipe_cache
               hit: saved recipe + original timestamp (no model)
               miss: original structured agent -> validation -> atomic save -> result
```

- **Service boundary:** FastAPI is the only browser API and owns profile validation, deterministic nutrition, and generation. Node has a narrower role: persist and retrieve versioned recipe data. It does not duplicate the food or profile APIs.
- **Exact reuse, not semantic matching:** The fingerprint depends on normalized ingredients, preparation-aware food IDs and labels, exact weights, dietary constraints, request hash, targets, and source/generator revisions. Changing these inputs does not silently reuse the old answer. The store retains the request hash, ingredient IDs/weights, normalized dietary constraints, the recipe, and its timestamp; it does not store the raw prompt or raw physical profile. A hash is not a privacy boundary on its own. Use a private database.
- **Failure handling:** A successful empty food query returns 200 with an empty array. An unknown food ID returns 404; an invalid serving returns 422. A missing saved recipe is normal only when the store returns the explicit lookup-miss response. A store outage produces 503 rather than spending model tokens or masking the error. Connection timeouts and bad upstream responses have distinct failure statuses. Nutrition stays independent.
- **Write semantics:** PostgreSQL enforces one key per record, and the first successful insert wins. FastAPI uses process-local locking to suppress duplicate model calls among concurrent matching requests in one worker. Deployments with multiple workers need distributed coordination if they require exactly one model call per concurrent miss.
- **Scope:** Existing terminal modules and CNF import are preserved. Recipe macros are estimates, not the authoritative calculated ingredient totals. No model credential goes to Node or React. The calibration seed is illustrative, not model-generated.
