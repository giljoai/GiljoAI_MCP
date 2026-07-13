import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

/**
 * useTokenActionPage — shared state machine for email-link "token action"
 * landing pages (dup-10: AccountDeletionCancel, AccountDeletionConfirm,
 * VerifyEmailChangePage). Token IS the auth for these public routes — no
 * JWT required.
 *
 * Reads `?token` from the route, calls `performAction(token)` once on
 * mount, and tracks loading/success/error state. On success `response`
 * holds the resolved API response (callers derive their own success text /
 * fields from it); on failure `errorDetail` holds
 * `err?.response?.data?.detail || ''`.
 */
export function useTokenActionPage(performAction) {
  const route = useRoute()
  const router = useRouter()

  const loading = ref(true)
  const success = ref(false)
  const response = ref(null)
  const errorDetail = ref('')

  const token = computed(() => route.query.token || '')
  const tokenMissing = computed(() => !token.value)

  function goLogin() {
    router.push('/login')
  }

  onMounted(async () => {
    if (tokenMissing.value) {
      loading.value = false
      return
    }
    try {
      response.value = await performAction(token.value)
      success.value = true
    } catch (err) {
      errorDetail.value = err?.response?.data?.detail || ''
      success.value = false
    } finally {
      loading.value = false
    }
  })

  return { loading, success, response, errorDetail, token, tokenMissing, goLogin }
}
