package com.centricsoftware.core.controller;
import com.alibaba.fastjson.JSONArray;
import com.centricsoftware.core.service.FSService;
import com.centricsoftware.commons.dto.ResEntity;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

/**
 * 飞书 Aily 接口调用控制层
 * 接口路径：/feishu/aily
 */
@Slf4j
@RestController
@RequestMapping("/feishu")  // 父路径 feishu
public class FSController {

    @Autowired
    private FSService fsService;

    /**
     * 调用飞书 Aily 接口
     * @param jsonArray 包含 PLM 前端传入的 URL 信息
     * @return 响应内容
     * @throws Exception
     */
    @RequestMapping(value = "/aily/gb2760", method = RequestMethod.POST, produces = "application/json; charset=utf-8")
    public ResEntity callGB2760(@RequestBody JSONArray jsonArray) throws Exception {
        log.info("飞书Aily接口接收参数：{}", jsonArray.toJSONString());
        ResEntity result = fsService.callAily(jsonArray);  // 调用 FSService 中的方法
        return result;
    }

    // 其他可能的接口可以按相同方式添加，例如：
    // @RequestMapping(value = "/aily/otherEndpoint", method = RequestMethod.POST)
    // public ResEntity callOtherEndpoint(@RequestBody JSONArray jsonArray) { ... }
}
