package com.centricsoftware.core.service;

import com.alibaba.fastjson.JSONArray;
import com.alibaba.fastjson.JSONObject;
import com.centricsoftware.commons.dto.ResEntity;
import com.centricsoftware.commons.dto.WebResponse;
import com.centricsoftware.commons.em.ResCode;
import com.centricsoftware.commons.utils.NodeUtil;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.lang3.StringEscapeUtils;
import org.springframework.stereotype.Service;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;


@Service
@Slf4j
public class FSService {

    // 固定的 app_id 和 app_secret
    private static final String APP_ID = "cli_a83c1dce493e900e";
    private static final String APP_SECRET = "XI3Ab3u68POC4sLvzLrrVhhmetycsJWV";
    private static final String SERVER_URL = "https://open.feishu.cn/open-apis";

    /**
     * 主要逻辑：提取 PLM 参数 → 获取 token → 构造 query → 调用 Aily → 返回结果
     */
    public ResEntity callAily(JSONArray jsonArray) throws Exception {
        try {
            for (int i = 0; i < jsonArray.size(); i++) {
                JSONObject jsonObject = jsonArray.getJSONObject(i);
                String url = jsonObject.getString("url");
                log.info("开始处理URL：{}", url);

                // step1: 获取 RecipeDataSheet 对象信息
                Map<String, String> recipeMap = NodeUtil.JSqueryAttributes(url);
                String revisionUrl = recipeMap.get("CurrentRevision");
                log.info("CurrentRevision = {}", revisionUrl);

                // step2: 进入 RecipeDataSheetRevision 获取 C8_RDS_Category
                Map<String, String> revisionMap = NodeUtil.JSqueryAttributes(revisionUrl);
                String categoryCode = revisionMap.get("C8_RDS_Category");
                log.info("category_code = {}", categoryCode);

                // step3: 从 RecipeDataSheet 获取 RecipeFoodLabel 字段
                String foodLabelUrl = recipeMap.get("RecipeFoodLabel");
                log.info("RecipeFoodLabel = {}", foodLabelUrl);

                // step4: 进入 FoodLabelDataSheet → CurrentRevision → FoodLabelDataSheetRevision
                Map<String, String> foodLabelMap = NodeUtil.JSqueryAttributes(foodLabelUrl);
                String foodRevisionUrl = foodLabelMap.get("CurrentRevision");
                Map<String, String> foodRevisionMap = NodeUtil.JSqueryAttributes(foodRevisionUrl);

                // step5: 获取 Ingredients (refvector 数组)
                String ingredientsRef = foodRevisionMap.get("Ingredients");
                log.info("Ingredients refvector = {}", ingredientsRef);

                List<JSONObject> ingredientsList = new ArrayList<>(); // 修改为 List<JSONObject>
                if (ingredientsRef != null && !ingredientsRef.isEmpty()) {
                    String[] ingredientUrls = ingredientsRef.replace("[", "")
                            .replace("]", "")
                            .split(",");
                    for (String ingUrl : ingredientUrls) {
                        ingUrl = ingUrl.trim();
                        if (ingUrl.isEmpty()) continue;
                        Map<String, String> ingMap = NodeUtil.JSqueryAttributes(ingUrl);
                        String name = ingMap.get("$Name");
                        log.info("name:" + name);
                        String ratio = ingMap.get("CalculatedPct");
                        String formattedRatio = (ratio != null) ? String.format("%.0f%%", Double.parseDouble(ratio) * 100) : "0%";  // 格式化比例为百分比
                        JSONObject ingJson = new JSONObject();
                        ingJson.put("name", name);  // 确保 name 被添加到 JSON 对象中
                        ingJson.put("ratio", formattedRatio);
                        ingredientsList.add(ingJson);  // 直接添加 JSON 对象
                    }
                }

                // step6: 组织 query JSON（压缩为一行）
                JSONObject queryJson = new JSONObject();
                queryJson.put("category_code", categoryCode);
                queryJson.put("ingredients", ingredientsList);  // 使用 List<JSONObject> 而不是转换为字符串
                String queryStr = queryJson.toJSONString();
                log.info("query 参数：{}", queryStr);


                // step7: 获取飞书 token
                String token = getFeishuToken();
                log.info("获取到的飞书 token：{}", token);

                // step8: 调用飞书 Aily 接口
                JSONObject globalVariable = new JSONObject();
                globalVariable.put("query", queryStr);
                JSONObject bodyJson = new JSONObject();
                bodyJson.put("global_variable", globalVariable);

                // 发送请求
                String responseBody = sendHttpRequest(token, bodyJson);
                // 打印原始响应内容，防止乱码（尝试重新以 UTF-8 解码）
                try {
                    String decodedResponse = new String(responseBody.getBytes(StandardCharsets.ISO_8859_1), StandardCharsets.UTF_8);
                    log.info("Aily接口原始响应（UTF-8）：{}", decodedResponse);
                } catch (Exception e) {
                    log.warn("Aily接口响应打印异常，原始内容：{}", responseBody);
                }

                // **修改8**: 直接将 Aily 接口返回的 `output` 字段写入 FoodLabelDataSheetRevision 的 Testresults 字段
                JSONObject respJson = JSONObject.parseObject(responseBody);
                String output = respJson.getJSONObject("data").getString("output");
                log.info("Aily接口返回的output：{}", output);  // **修改9**: 打印 `output` 字段，确认其内容

                String cleanOutput = output
                        .replaceFirst("\\{\"answer\":\"", "")   // 去掉开头的 {"answer":"
                        .replaceAll("\"\\}\"", "")              // 去掉结尾的 "}
                        .replace("{", "")                      // 去掉花括号 {
                        .replace("}", "")                      // 去掉花括号 }
                        .replaceAll("\\n+", "")                // 去掉多余的换行符
                        .replaceAll("&lt;", "<")               // 将转义的<还原
                        .replaceAll("&gt;", ">")               // 将转义的>还原
                        .replaceAll("&quot;", "\"");           // 将转义的"还原

                String escapedOutput = StringEscapeUtils.escapeXml10(cleanOutput);
                log.info("转义后的：",escapedOutput);
                // **替换换行符为 HTML <br> 或保留原有的换行符**
                cleanOutput = escapedOutput.replace("\n", "<br>");
                log.info("替换换行符后的：",cleanOutput);

                // 使用 OAServiceUtils.setFiledVale 方法直接更新 Testresults 字段
                OAServiceUtils.setFiledVale(foodRevisionUrl, "Testresults", cleanOutput,"string");



                return WebResponse.success(ResCode.SUCCESS); // 直接返回成功，使用默认的消息和代码
            }
        } catch (Exception e) {
            log.error("调用飞书 Aily 接口出错：", e);
            return WebResponse.error("调用飞书 Aily 接口出错：" + e.getMessage());
        }
        return WebResponse.error("FAIL");
    }

    /**
     * 获取飞书 tenant_access_token
     */
    private String getFeishuToken() throws Exception {
        String tokenUrl = SERVER_URL + "/auth/v3/tenant_access_token/internal";
        HttpURLConnection connection = (HttpURLConnection) new URL(tokenUrl).openConnection();
        connection.setRequestMethod("POST");
        connection.setDoOutput(true);
        connection.setRequestProperty("Content-Type", "application/json");

        // 创建请求体
        String requestBody = String.format("{\"app_id\":\"%s\",\"app_secret\":\"%s\"}", APP_ID, APP_SECRET);
        try (OutputStream os = connection.getOutputStream()) {
            byte[] input = requestBody.getBytes(StandardCharsets.UTF_8);
            os.write(input, 0, input.length);
        }

        // 获取响应
        BufferedReader reader = new BufferedReader(new InputStreamReader(connection.getInputStream()));
        StringBuilder response = new StringBuilder();
        String line;
        while ((line = reader.readLine()) != null) {
            response.append(line);
        }
        reader.close();

        // 解析返回的 JSON
        String json = response.toString();
        log.info("获取 token 响应：{}", json);
        JSONObject jsonResponse = JSONObject.parseObject(json);
        return jsonResponse.getString("tenant_access_token");
    }

    /**
     * 发送 HTTP 请求到飞书 Aily 接口
     */
    private String sendHttpRequest(String token, JSONObject bodyJson) throws Exception {
        String url = "https://open.feishu.cn/open-apis/aily/v1/apps/spring_24208e1b94__c/skills/skill_1cdf9d94735d/start";
        HttpURLConnection connection = (HttpURLConnection) new URL(url).openConnection();
        // 设置超时时间（单位：毫秒）
        connection.setConnectTimeout(50000);  // 设置连接超时时间为30秒
        connection.setReadTimeout(50000);     // 设置读取超时时间为30秒
        connection.setRequestMethod("POST");
        connection.setDoOutput(true);
        connection.setRequestProperty("Authorization", "Bearer " + token);
        connection.setRequestProperty("Content-Type", "application/json");

        // 创建请求体
        String requestBody = bodyJson.toJSONString();
        try (OutputStream os = connection.getOutputStream()) {
            byte[] input = requestBody.getBytes(StandardCharsets.UTF_8);
            os.write(input, 0, input.length);
        }

        // 获取响应
        BufferedReader reader = new BufferedReader(new InputStreamReader(connection.getInputStream()));
        StringBuilder response = new StringBuilder();
        String line;
        while ((line = reader.readLine()) != null) {
            response.append(line);
        }
        reader.close();

        return response.toString();
    }
}
