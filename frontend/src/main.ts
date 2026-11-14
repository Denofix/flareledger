import { createApp } from "vue";
import { createRouter, createWebHistory } from "vue-router";
import App from "./App.vue";
import CatalogView from "./views/CatalogView.vue";
import InvestigationView from "./views/InvestigationView.vue";
import MeasurementsView from "./views/MeasurementsView.vue";
import EvidenceView from "./views/EvidenceView.vue";
import AskView from "./views/AskView.vue";
import RecordView from "./views/RecordView.vue";
import NotFoundView from "./views/NotFoundView.vue";
import "./style.css";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", component: CatalogView, meta: { label: "Investigations" } },
    {
      path: "/investigations/:id",
      component: InvestigationView,
      meta: { label: "Investigation" },
    },
    {
      path: "/measurements",
      component: MeasurementsView,
      meta: { label: "Measurements" },
    },
    {
      path: "/compare",
      component: MeasurementsView,
      meta: { label: "Compare measurements" },
    },
    {
      path: "/evidence",
      component: EvidenceView,
      meta: { label: "Evidence search" },
    },
    {
      path: "/sources/:id",
      component: RecordView,
      props: { kind: "sources" },
      meta: { label: "Source record" },
    },
    {
      path: "/evidence/:id",
      component: RecordView,
      props: { kind: "evidence" },
      meta: { label: "Source evidence" },
    },
    {
      path: "/records/:id",
      component: RecordView,
      props: { kind: "records" },
      meta: { label: "Research record" },
    },
    { path: "/ask", component: AskView, meta: { label: "Ask FlareLedger" } },
    {
      path: "/:pathMatch(.*)*",
      component: NotFoundView,
      meta: { label: "Page not found" },
    },
  ],
  scrollBehavior: () => ({ top: 0 }),
});
router.afterEach((to) => {
  document.title = `${String(to.meta.label || "Research")} - FlareLedger`;
});
createApp(App).use(router).mount("#app");
