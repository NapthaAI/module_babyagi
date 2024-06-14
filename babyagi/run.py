import json
import asyncio
from typing import Dict
from naptha_sdk.task import Task as NapthaTask
from naptha_sdk.client.node import Node
from babyagi.utils import get_logger
from babyagi.schemas import InputSchema

logger = get_logger(__name__)


async def run(inputs: InputSchema, worker_nodes, orchestrator_node, flow_run, cfg: Dict):

    # get initial task lists
    task_list_task = NapthaTask(
        name="task_list_task",
        fn="babyagi_task_initiator",
        worker_node=worker_nodes[0],
        orchestrator_node=orchestrator_node,
        flow_run=flow_run
    )

    # task_execution_task
    task_execution_task = NapthaTask(
        name="task_execution_task",
        fn="babyagi_task_executor",
        worker_node=worker_nodes[1],
        orchestrator_node=orchestrator_node,
        flow_run=flow_run
    )

    # task_finalizer_task
    task_finalizer_task = NapthaTask(
        name="task_finalizer_task",
        fn="babyagi_task_finalizer",
        worker_node=worker_nodes[0],
        orchestrator_node=orchestrator_node,
        flow_run=flow_run
    )

    task_list = await task_list_task(objective=inputs.objective)
    logger.info(f"Initial task list: {task_list}")

    task_list = json.loads(task_list)
    for task in task_list['list']:
        task['done'] = False

    tasks_to_perform = [task for task in task_list['list'] if not task['done']]
    count_num_outstanding_tasks = len(tasks_to_perform)

    logger.info(f"Number of outstanding tasks: {count_num_outstanding_tasks}")

    while count_num_outstanding_tasks > 0:
        logger.info(f"Performing {count_num_outstanding_tasks} tasks")

        for task in tasks_to_perform:
            task_str = f"Task Name: {task['name']}\nTask Description: {task['description']}\n"
            task_response = await task_execution_task(task=task_str, objective=inputs.objective)
            logger.info(f"Task response: {task_response}")

            task['result'] = task_response
            task['done'] = True

        tasks_str = ""
        for task in task_list['list']:
            tasks_str += f"Task Name: {task['name']}\nTask Description: {task['description']}\nTask Result: {task['result']}\nDone: {task['done']}\n"
        logger.info(f"Final task list: {tasks_str}")

        task_finalizer_response = await task_finalizer_task(task=tasks_str, objective=inputs.objective)
        logger.info(f"Task finalizer response: {task_finalizer_response}")

        task_finalizer_response = json.loads(task_finalizer_response)

        count_num_outstanding_tasks = len([task for task in task_list['list'] if not task['done']])
        logger.info(f"Number of outstanding tasks: {count_num_outstanding_tasks}")


    logger.info(f"Completed task list: {task_finalizer_response}")

    task_list['list'].append(
        {
            'name': "Finalizer Task",
            'description': "Finalizer Task",
            'done': True,
            'result':task_finalizer_response['final_report']
        }
    )

    return json.dumps(task_list)

