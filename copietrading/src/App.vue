<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

const channels = ref([])
const selectedChannel = ref(null)
const messages = ref([])
const loading = ref(false)

const fetchChannels = async () => {
  try {
    const response = await axios.get('http://localhost:5000/channels')
    channels.value = response.data
  } catch (error) {
    console.error('Error fetching channels:', error)
  }
}

const fetchMessages = async (channelId) => {
  loading.value = true
  try {
    const response = await axios.get(`http://localhost:5000/messages/${channelId}`)
    messages.value = response.data
    selectedChannel.value = channels.value.find(c => c.id === channelId)
  } catch (error) {
    console.error('Error fetching messages:', error)
  } finally {
    loading.value = false
  }
}

onMounted(fetchChannels)
</script>

<template>
  <div class="min-h-screen bg-gray-100 p-8">
    <div class="max-w-4xl mx-auto">
      <h1 class="text-3xl font-bold mb-8">Telegram Channel Viewer</h1>
      
      <!-- Channel Selection -->
      <div class="bg-white rounded-lg shadow p-6 mb-8">
        <h2 class="text-xl font-semibold mb-4">Sélectionnez un canal</h2>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <button
            v-for="channel in channels"
            :key="channel.id"
            @click="fetchMessages(channel.id)"
            :class="[
              'p-4 rounded-lg text-left transition',
              selectedChannel?.id === channel.id
                ? 'bg-blue-500 text-white'
                : 'bg-gray-50 hover:bg-gray-100'
            ]"
          >
            <div class="font-medium">{{ channel.title }}</div>
            <div class="text-sm opacity-75">{{ channel.type }}</div>
          </button>
        </div>
      </div>
      
      <!-- Messages Display -->
      <div v-if="selectedChannel" class="bg-white rounded-lg shadow p-6">
        <h2 class="text-xl font-semibold mb-4">
          Messages de {{ selectedChannel.title }}
        </h2>
        
        <div v-if="loading" class="text-center py-8">
          Chargement des messages...
        </div>
        
        <div v-else class="space-y-6">
          <div
            v-for="message in messages"
            :key="message.id"
            class="border rounded-lg p-4"
          >
            <div class="flex justify-between mb-2">
              <span class="text-sm text-gray-500">ID: {{ message.id }}</span>
              <span class="text-sm text-gray-500">{{ new Date(message.date).toLocaleString() }}</span>
            </div>
            <div class="text-gray-700">{{ message.text }}</div>
            
            <!-- Reply -->
            <div
              v-if="message.reply_to"
              class="mt-4 ml-4 p-3 bg-gray-50 rounded border-l-4 border-gray-300"
            >
              <div class="text-sm text-gray-500 mb-1">
                En réponse à (ID: {{ message.reply_to.id }})
              </div>
              <div class="text-gray-600">{{ message.reply_to.text }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style>
@tailwind base;
@tailwind components;
@tailwind utilities;
</style>