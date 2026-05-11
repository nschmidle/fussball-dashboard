<template>
  <div>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark mb-4">
      <div class="container">
        <router-link class="navbar-brand" to="/">⚽ Fußball Dashboard</router-link>
        <div class="navbar-nav">
          <router-link class="nav-link" to="/">Dashboard</router-link>
          <router-link class="nav-link" to="/matches">Spiele</router-link>
          <router-link class="nav-link" to="/standings">Tabelle</router-link>
          <router-link class="nav-link" to="/stats">Statistiken</router-link>
        </div>
      </div>
    </nav>
    <div class="container">
      <router-view />
    </div>
  </div>
</template>
