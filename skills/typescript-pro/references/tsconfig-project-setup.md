# tsconfig & Project Setup

## Strict Mode

`"strict": true` turns on `noImplicitAny`, `strictNullChecks`, `strictFunctionTypes`, and several other flags together. Enable it on day one of a new project — retrofitting strict mode onto a large `any`-riddled codebase later is far more expensive than starting with it.

## Extra Strictness Worth Enabling

```json
{
  "compilerOptions": {
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true,
    "noImplicitOverride": true,
    "noFallthroughCasesInSwitch": true
  }
}
```

`noUncheckedIndexedAccess` in particular catches a common real bug: indexing into an array or record and assuming the result isn't `undefined`.

## Module Resolution

Match `moduleResolution` to the actual runtime: `bundler` for a project built by Vite/esbuild/webpack, `node16`/`nodenext` for a Node.js package that ships its own compiled output and needs correct `.js` extension resolution.

## Project References

For a monorepo with multiple packages that depend on each other, use TypeScript project references (`"references": [{ "path": "../shared" }]`) so `tsc --build` only recompiles what actually changed, instead of type-checking the whole repo from a single root config.
