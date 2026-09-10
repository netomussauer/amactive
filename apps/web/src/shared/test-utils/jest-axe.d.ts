import 'vitest'
import type { AxeMatchers } from 'jest-axe'

// Module augmentation requires `interface` (not `type`) for declaration
// merging with vitest's own Assertion/AsymmetricMatchersContaining types.
/* eslint-disable @typescript-eslint/no-empty-object-type, @typescript-eslint/no-unused-vars */
declare module 'vitest' {
  interface Assertion<T = unknown> extends AxeMatchers {}
  interface AsymmetricMatchersContaining extends AxeMatchers {}
}
