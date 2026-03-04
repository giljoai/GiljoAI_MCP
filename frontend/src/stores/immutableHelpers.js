/**
 * Small immutable helpers used by the 0379 reactive store migrations.
 * Keep these utilities generic and dependency-free.
 */

export function immutableMapSet(map, key, value) {
  const next = new Map(map)
  next.set(key, value)
  return next
}

export function immutableObjectPatch(obj, patch) {
  return { ...(obj || {}), ...(patch || {}) }
}
