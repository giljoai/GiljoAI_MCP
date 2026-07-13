/**
 * useProductVisionUpload.js — FE-6006 unit 3b
 *
 * Encapsulates the vision-file upload flow for ProductsView:
 *   - Client-side file validation
 *   - Auto-create product in create mode (silent save to get UUID)
 *   - Per-file upload with progress tracking
 *   - Toast notifications per file
 *   - Refresh existing docs list after upload
 *
 * The composable returns upload state refs plus the handler function.
 * The caller owns `editingProduct` and `autoSavedForAnalysis` — they
 * are passed in so mutations propagate back to the view.
 */
import { ref } from 'vue'
import { useToast } from '@/composables/useToast'
import { useProductStore } from '@/stores/products'
import { validateUploadFiles } from '@/utils/uploadValidation'
import { parseErrorResponse } from '@/utils/errorMessages'
import api from '@/services/api'

export function useProductVisionUpload({ editingProduct, autoSavedForAnalysis }) {
  const { showToast } = useToast()
  const productStore = useProductStore()

  const visionFiles = ref([])
  const uploadingVision = ref(false)
  const uploadProgress = ref(0)
  const visionUploadError = ref(null)
  const existingVisionDocuments = ref([])

  async function loadExistingVisionDocuments(productId) {
    try {
      const response = await api.visionDocuments.listByProduct(productId)
      existingVisionDocuments.value = response.data || []
    } catch (error) {
      console.error('[useProductVisionUpload] Failed to load vision documents:', error)
      existingVisionDocuments.value = []
    }
  }

  function validateFiles(files) {
    visionFiles.value = files
    const result = validateUploadFiles(files)
    if (result.valid) return true
    const firstFailure = result.invalid[0]
    showToast({
      message: `${firstFailure.file?.name || 'File'}: ${firstFailure.message}`,
      type: 'error',
      timeout: 7000,
    })
    visionFiles.value = []
    return false
  }

  // SEC-0001 Phase 2: client-side pre-check mirrors backend UploadConfig.
  // Backend (api/endpoints/vision_documents.py + upload_guard.py) remains
  // the authoritative security boundary.
  async function uploadVisionFilesOnAttach({ productName, files }) {
    if (!files || files.length === 0) return
    if (!validateFiles(files)) return

    try {
      let productId
      if (editingProduct.value) {
        productId = editingProduct.value.id
      } else {
        // In create mode: silently create the product to get a UUID
        const product = await productStore.createProduct({ name: productName })
        editingProduct.value = product
        autoSavedForAnalysis.value = product.id
        productId = product.id
      }

      uploadingVision.value = true
      uploadProgress.value = 0
      visionUploadError.value = null

      for (let i = 0; i < files.length; i++) {
        const file = files[i]
        try {
          const formData = new FormData()
          formData.append('product_id', productId)
          formData.append('document_name', file.name.replace(/\.[^/.]+$/, ''))
          formData.append('document_type', 'vision')
          formData.append('vision_file', file)
          formData.append('auto_chunk', 'true')

          const response = await api.visionDocuments.upload(formData)
          uploadProgress.value = ((i + 1) / files.length) * 100

          const chunkCount = response.data?.chunk_count || 0
          const isSummarized = response.data?.is_summarized || false
          const statusParts = []
          if (isSummarized) statusParts.push('analyzed')
          if (chunkCount > 0) statusParts.push(`${chunkCount} chunks`)

          showToast({
            message: `${file.name} uploaded${statusParts.length ? ` (${statusParts.join(', ')})` : ''}`,
            type: 'success',
            timeout: 3000,
          })
        } catch (uploadError) {
          console.error(`[useProductVisionUpload] Failed to upload ${file.name}:`, uploadError)

          // SEC-0001 Phase 2: Surface backend {error_code, message} verbatim
          // (UPLOAD_TOO_LARGE / UPLOAD_TYPE_NOT_ALLOWED / UPLOAD_CONTENT_NOT_TEXT /
          // UPLOAD_FILENAME_INVALID). 409 gets dedicated UX copy.
          let errorMessage
          if (uploadError?.response?.status === 409) {
            errorMessage = `${file.name}: Document already exists. Please rename and try again.`
          } else if (uploadError?.response) {
            const parsed = parseErrorResponse(uploadError)
            errorMessage = `${file.name}: ${parsed.message || 'Upload failed'}`
          } else {
            errorMessage = `Failed to upload ${file.name}`
          }

          visionUploadError.value = errorMessage
          showToast({ message: errorMessage, type: 'error', timeout: 7000 })
        }
      }

      uploadingVision.value = false
      visionFiles.value = []
      await loadExistingVisionDocuments(productId)
    } catch (error) {
      console.error('[useProductVisionUpload] Failed to upload vision files:', error)
      uploadingVision.value = false
      showToast({
        message: 'Failed to upload files. Check your connection and try again.',
        type: 'error',
        timeout: 5000,
      })
    }
  }

  function resetUploadState() {
    visionFiles.value = []
    existingVisionDocuments.value = []
    uploadingVision.value = false
    uploadProgress.value = 0
    visionUploadError.value = null
  }

  return {
    visionFiles,
    uploadingVision,
    uploadProgress,
    visionUploadError,
    existingVisionDocuments,
    loadExistingVisionDocuments,
    uploadVisionFilesOnAttach,
    resetUploadState,
  }
}
