/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { SearchBar } from "@web/search/search_bar/search_bar";
import { registry } from "@web/core/registry";
import { fuzzyTest } from "@web/core/utils/search";
const parsers = registry.category("parsers");

let nextItemId = 1;

const CHAR_FIELDS = ["char", "html", "many2many", "many2one", "one2many", "text"];

patch(SearchBar.prototype, {
    //---- Handlers ----

    async computeState(options = {}, search_item=true) {
        const query = "query" in options ? options.query : this.state.query;
        const expanded = "expanded" in options ? options.expanded : this.state.expanded;
        const focusedIndex =
            "focusedIndex" in options ? options.focusedIndex : this.state.focusedIndex;
        const subItems = "subItems" in options ? options.subItems : this.subItems;

        const tasks = [];
        for (const id of expanded) {
            if (!subItems[id]) {
                tasks.push({ id, prom: this.computeSubItems(id, query) });
            }
        }

        const prom = this.keepLast.add(Promise.all(tasks.map((task) => task.prom)));
        if (tasks.length) {
            const taskResults = await prom;
            tasks.forEach((task, index) => {
                subItems[task.id] = taskResults[index];
            });
        }

        this.state.expanded = expanded;
        this.state.query = query;
        this.state.focusedIndex = focusedIndex;
        this.subItems = subItems;

        this.inputRef.el.value = query;

        const trimmedQuery = this.state.query.trim();

        this.items.length = 0;
        if (!trimmedQuery) {
            return;
        }

        for (const searchItem of this.searchItems) {
            const field = this.fields[searchItem.fieldName];
            const type = field.type === "reference" ? "char" : field.type;
            /** @todo do something with respect to localization (rtl) */
            const preposition = this.env._t(["date", "datetime"].includes(type) ? "at" : "for");

            if (["selection", "boolean"].includes(type)) {
                const options = field.selection || [
                    [true, this.env._t("Yes")],
                    [false, this.env._t("No")],
                ];
                for (const [value, label] of options) {
                    if (fuzzyTest(trimmedQuery.toLowerCase(), label.toLowerCase())) {
                        console.log('+++++++++++++++++++++++')
                        this.items.push({
                            id: nextItemId++,
                            searchItemDescription: searchItem.description,
                            preposition,
                            searchItemId: searchItem.id,
                            label,
                            /** @todo check if searchItem.operator is fine (here and elsewhere) */
                            operator: searchItem.operator || "=",
                            value,
                        });
                    }
                }
                continue;
            }

            const parser = parsers.contains(type) ? parsers.get(type) : (str) => str;
            let value;
            try {
                switch (type) {
                    case "date": {
                        value = serializeDate(parser(trimmedQuery));
                        break;
                    }
                    case "datetime": {
                        value = serializeDateTime(parser(trimmedQuery));
                        break;
                    }
                    case "many2one": {
                        value = trimmedQuery;
                        break;
                    }
                    default: {
                        value = parser(trimmedQuery);
                    }
                }
            } catch (_e) {
                continue;
            }
            console.log('_____________');
            const item = {
                id: nextItemId++,
                searchItemDescription: searchItem.description,
                preposition,
                searchItemId: searchItem.id,
                label: this.state.query,
                operator: searchItem.operator || (CHAR_FIELDS.includes(type) ? "ilike" : "="),
                value,
            };
            if (type === "many2one") {
                item.isParent = true;
                item.isExpanded = this.state.expanded.includes(item.searchItemId);
            }

            this.items.push(item);
            if (item.isExpanded) {
                this.items.push(...this.subItems[searchItem.id]);
            }
            else{
                if (search_item && item.isParent){
                    this.toggleItem(item, !item.isExpanded);
                }
            }
        }
    },

    /**
     * @param {number} searchItemId
     * @param {string} query
     * @returns {Object[]}
     */
    async computeSubItems(searchItemId, query) {
        const searchItem = this.searchItems.find((i) => i.id === searchItemId);
        const field = this.fields[searchItem.fieldName];
        let domain = [];
        if (searchItem.domain) {
            try {
                domain = new Domain(searchItem.domain).toList();
            } catch (_e) {
                // Pass
            }
        }
        const options = await this.orm.call(field.relation, "name_search", [], {
            args: domain,
            context: field.context,
            limit: 8,
            name: query.trim(),
        });
        const subItems = [];
        if (options.length) {
            const operator = searchItem.operator || "=";
            for (const [value, label] of options) {
                subItems.push({
                    id: nextItemId++,
                    isChild: true,
                    searchItemId,
                    value,
                    label,
                    operator,
                });
            }
        } else {
            subItems.push({
                id: nextItemId++,
                isChild: true,
                searchItemId,
                label: this.env._t("(no result)"),
                unselectable: true,
            });
        }
        return subItems;
    },

    toggleItem(item, shouldExpand) {
        const id = item.searchItemId;
        const expanded = [...this.state.expanded];
        const index = expanded.findIndex((id0) => id0 === id);
        if (shouldExpand === true) {
            if (index < 0) {
                expanded.push(id);
            }
        } else {
            if (index >= 0) {
                expanded.splice(index, 1);
            }
        }
        this.computeState({ expanded }, shouldExpand);
    }
});