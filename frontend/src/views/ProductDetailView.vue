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

        <v-card v-else-if="product">
          <v-card-text>
            <v-row>
              <v-col cols="12" md="6">
                <div class="text-subtitle-2 text-medium-emphasis">Product ID</div>
                <div class="text-body-1">{{ product.id }}</div>
              </v-col>
              <v-col cols="12" md="6">
                <div class="text-subtitle-2 text-medium-emphasis">Created</div>
                <div class="text-body-1">{{ formatDate(product.created_at) }}</div>
              </v-col>
              <v-col cols="12">
                <div class="text-subtitle-2 text-medium-emphasis">Description</div>
                <div class="text-body-1">{{ product.description || 'No description' }}</div>
              </v-col>
              <v-col v-if="product.vision_path" cols="12">
                <div class="text-subtitle-2 text-medium-emphasis">Vision Path</div>
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

const route = useRoute()
const productStore = useProductStore()

const product = ref(null)
const loading = ref(true)

function formatDate(dateStr) {
  if (!dateStr) return 'N/A'
  return new Date(dateStr).toLocaleString()
}

onMounted(async () => {
  loading.value = true
  try {
    product.value = await productStore.fetchProductById(route.params.id)
  } finally {
    loading.value = false
  }
})
</script>
