<template>
  <v-container fluid>
    <v-row>
      <v-col cols="12">
        <v-btn icon variant="text" class="mb-4" @click="$router.back()">
          <v-icon>mdi-arrow-left</v-icon>
        </v-btn>

        <h1 class="text-h4 mb-4">{{ product?.name || 'Product Details' }}</h1>

        <v-card v-if="loading">
          <v-card-text class="text-center py-8">
            <v-progress-circular indeterminate color="primary"></v-progress-circular>
          </v-card-text>
        </v-card>

        <v-card v-else-if="product" class="smooth-border" style="border-radius: 12px">
          <v-card-text>
            <v-row>
              <v-col cols="12" md="6">
                <div class="text-subtitle-2" style="color: #8895a8">Product ID</div>
                <div class="text-body-1 font-monospace" style="color: #a3aac4; font-size: 0.75rem">{{ product.id }}</div>
              </v-col>
              <v-col cols="12" md="6">
                <div class="text-subtitle-2" style="color: #8895a8">Created</div>
                <div class="text-body-1">{{ formatDateTime(product.created_at) }}</div>
              </v-col>
              <v-col cols="12">
                <div class="text-subtitle-2" style="color: #8895a8">Description</div>
                <div class="text-body-1">{{ product.description || 'No description' }}</div>
              </v-col>
              <v-col v-if="product.vision_path" cols="12">
                <div class="text-subtitle-2" style="color: #8895a8">Vision Path</div>
                <div class="text-body-1">{{ product.vision_path }}</div>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useProductStore } from '@/stores/products'
import { useFormatDate } from '@/composables/useFormatDate'

const route = useRoute()
const productStore = useProductStore()

const product = ref(null)
const loading = ref(true)

const { formatDateTime } = useFormatDate()

onMounted(async () => {
  loading.value = true
  try {
    product.value = await productStore.fetchProductById(route.params.id)
  } finally {
    loading.value = false
  }
})
</script>
