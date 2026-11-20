# MacroChef web frontend

This is the React/Vite client for the local technical demo. It reads food search and portion calculations from FastAPI and supports multi-ingredient meal totals plus profile-based recipe requests. No LLM provider calls, tracking, browser secrets, or external API credentials are used in the frontend.

## Develop

With Node.js 22+ and the demo FastAPI backend listening at `127.0.0.1:8000`:

```bash
npm ci
npm run dev
npm test
npm run build
```

The Vite dev server proxies /api to FastAPI. The production build uses same-origin /api; serve dist from the FastAPI demo (or proxy /api on your host). Don't open index.html directly from disk.

## Verify the flow

- Search for an ingredient, distinguish cooked and dry, and select a result.
- Change the portion with the keyboard, stepper, or direct input. The API sends calculated values for the current serving only. Superseded searches/calculations abort; only results matching the current request are displayed.
- Add different portions, check their combined nutrition, and remove a serving. Retry after a disconnected backend and confirm an unavailable nutrient is not presented as zero.
- Open Make a meal, fill the nutrition profile and separate recipe request, then select Generate recipe. A completed result shows cooking time, estimated nutrition, ingredient amounts and instructions. Reused results display Saved recipe.
- Hover/tap the glass action, tab to its focus ring, and enable reduced motion. The label remains still and announces calculating; animation is decorative and tied to the actual request.

Recipe suggestions are fetched from the demo backend. The UI sends data only to the same-origin FastAPI application and makes a recipe request only when the form is submitted. It does not save profile fields to browser storage. Nutrition lookup and meal totals remain available if generation fails. The CSS lens is simulated, not native Apple material. Treat the bundled demo as an engineering sample, not a production nutrition service.
