<script setup>
import { useUser } from '@/utils/user'
const { userInfo } = useUser()
</script>

<template>
    <div>欢迎您: {{ userInfo?.username }}</div>
</template>

<style scoped>

</style>